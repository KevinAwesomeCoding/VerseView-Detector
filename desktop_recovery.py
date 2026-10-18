"""Private, bounded sermon checkpoints. No settings, commands, or provider logs."""
import copy
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path
import tempfile
import threading

MAX_BYTES = 8 * 1024 * 1024
MAX_TEXT = 500_000


class RecoveryError(ValueError):
    pass


def sermon_data(raw):
    """Project only restorable content; reject malformed context rather than guess."""
    if not isinstance(raw, dict):
        raise RecoveryError('Recovery content is invalid.')
    def text(value, limit):
        if not isinstance(value, str) or len(value) > limit:
            raise RecoveryError('Recovery content is invalid or exceeds its size limit.')
        return value
    def number(value):
        if value is None or value == '': return None
        if type(value) is int and 1 <= value <= 200: return str(value)
        if isinstance(value, str) and re.fullmatch(r'[0-9]{1,3}', value) and 1 <= int(value) <= 200:
            return value
        raise RecoveryError('Recovery verse context is invalid.')
    def book(value):
        return None if value is None else text(value, 64)
    cited, history = raw.get('verses_cited', []), raw.get('verse_history', [])
    if not isinstance(cited, list) or not isinstance(history, list) or max(len(cited), len(history)) > 4096:
        raise RecoveryError('Recovery history is invalid or exceeds its size limit.')
    anchor = raw.get('sermon_anchor') or {}
    if not isinstance(anchor, dict): raise RecoveryError('Recovery verse context is invalid.')
    rows = []
    for row in history:
        if not isinstance(row, dict): raise RecoveryError('Recovery history is invalid.')
        rows.append({'ref': text(row.get('ref', ''), 128), 'time': text(row.get('time', ''), 32),
                     'layer': text(row.get('layer', ''), 64)})
    languages = raw.get('stream_languages', {})
    if not isinstance(languages, dict): raise RecoveryError('Recovery language metadata is invalid.')
    preview = raw.get('raw_preview', {})
    if not isinstance(preview, dict): raise RecoveryError('Recovery preview is invalid.')
    return {'transcript': text(raw.get('transcript', ''), MAX_TEXT),
            'transcript_secondary': text(raw.get('transcript_secondary', ''), MAX_TEXT),
            'verses_cited': [text(ref, 128) for ref in cited], 'verse_history': rows,
            'current_book': book(raw.get('current_book')), 'current_chapter': number(raw.get('current_chapter')),
            'current_verse': number(raw.get('current_verse')),
            'sermon_anchor': {'book': book(anchor.get('book')), 'chapter': number(anchor.get('chapter')), 'verse': number(anchor.get('verse'))},
            'stream_languages': {role: languages.get(role) if languages.get(role) in ('en', 'ml', 'hi', 'multi') else 'und'
                                 for role in ('primary', 'secondary')},
            'raw_preview': {role: text(preview.get(role, ''), 2000) for role in ('primary', 'secondary')}}


def meaningful(data):
    return bool(data['transcript'].strip() or data['transcript_secondary'].strip() or data['verse_history'] or data['verses_cited']
                or any(data['raw_preview'].values()))


class SessionRecovery:
    def __init__(self, profile):
        self.path = Path(profile) / 'Recovery' / 'session.json'
        self.lock = threading.RLock()
        self.staged = None
        self.active = False
        self.pending = False
        self.fresh_start = True
        self.error = ''
        self._signature = object()
        self.record = None
        self.revision = None
        self.refresh()

    def _stat(self):
        try:
            stat = self.path.lstat()
            return (stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_mode)
        except FileNotFoundError: return None
        except OSError: return (0, MAX_BYTES + 1, 0, 0)

    def refresh(self):
        with self.lock:
            signature = self._stat()
            if signature == self._signature: return
            if self.active and signature is not None:
                # Do not overwrite an externally replaced checkpoint, even
                # while recognition continues. Decisions still require Stop.
                self.active = False
            self._signature = signature
            self.staged = None
            self.record, self.revision, self.error = None, None, ''
            if signature is None:
                self.pending = False
                return
            self.pending = not self.active
            # An identity still allows explicit discard of malformed/oversized
            # files. Symlinks are never followed, including during discard.
            self.revision = hashlib.sha256(repr(signature).encode()).hexdigest()[:32]
            try:
                if self.path.is_symlink() or not self.path.is_file() or signature[1] > MAX_BYTES:
                    raise RecoveryError('Invalid recovery file')
                descriptor = os.open(self.path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
                with os.fdopen(descriptor, 'rb') as handle: raw = handle.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES: raise RecoveryError('Recovery file too large')
                value = json.loads(raw)
                if not isinstance(value, dict) or value.get('schema') != 1 or value.get('reason') not in ('autosave', 'stopped', 'error'):
                    raise RecoveryError('Invalid recovery file')
                saved = value.get('saved_at')
                if not isinstance(saved, str) or len(saved) > 64: raise RecoveryError('Invalid save time')
                dt.datetime.fromisoformat(saved)
                data = sermon_data(value.get('data'))
                if not meaningful(data): raise RecoveryError('Empty recovery file')
                self.record = {'schema': 1, 'saved_at': saved, 'reason': value['reason'], 'data': data}
                self.revision = hashlib.sha256(raw).hexdigest()[:32]
            except (OSError, ValueError, TypeError):
                self.error = 'Recovery file could not be read. It was retained; explicitly discard it to start fresh.'

    def snapshot(self):
        with self.lock:
            self.refresh()
            data = self.record['data'] if self.record else None
            status = 'staged' if self.staged else 'invalid' if self.pending and not self.record else 'available' if self.pending else 'saved' if self.record else 'none'
            # Historical previews stay separate from live STT and acceptance.
            return {'status': status, 'revision': self.revision, 'message': self.error,
                    'saved_at': self.record['saved_at'] if self.record else '',
                    'reason': self.record['reason'] if self.record else '',
                    'verse_count': len(data['verse_history']) if data else 0,
                    'preview': ({'primary': data['raw_preview']['primary'] or data['transcript'][-2000:],
                                 'secondary': data['raw_preview']['secondary'] or data['transcript_secondary'][-2000:],
                                 'sources': {role: 'speech' if data['raw_preview'][role] else 'context' for role in ('primary', 'secondary')},
                                 'languages': data['stream_languages'], 'references': [row['ref'] for row in data['verse_history'][-10:]]}
                                if data and status in ('available', 'staged') else None)}

    def choose(self, revision, restore):
        with self.lock:
            self.refresh()
            if self.active or not (self.pending or self.staged) or revision != self.revision:
                raise RecoveryError('Recovery changed or is no longer awaiting a decision. Refresh before acting.')
            if restore:
                if not self.record: raise RecoveryError('This recovery file is invalid. It cannot be restored.')
                self.staged = copy.deepcopy(self.record['data'])
                self.pending = False
                self.fresh_start = False
            else:
                try: self.path.unlink()
                except OSError: raise RecoveryError('Could not discard the recovery file. It was retained.') from None
                self.staged, self.record, self.revision = None, None, None
                self._signature = None
                self.pending, self.error = False, ''
                self.fresh_start = True

    def for_start(self):
        with self.lock:
            self.refresh()
            if self.pending: raise RecoveryError('Choose Restore or Discard for the saved session before starting.')
            return copy.deepcopy(self.staged)

    def started(self):
        with self.lock:
            self.staged = None
            self.pending = False
            self.active = True
            self.fresh_start = False

    def save(self, raw, reason):
        with self.lock:
            self.refresh()
            if self.pending or self.staged:
                raise RecoveryError('An unresolved recovery file was retained.')
            if reason not in ('autosave', 'stopped', 'error'):
                raise RecoveryError('Invalid checkpoint reason.')
            data = sermon_data(raw)
            if not meaningful(data): return False
            value = {'schema': 1, 'saved_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'reason': reason, 'data': data}
            encoded = json.dumps(value, ensure_ascii=False).encode('utf-8')
            if len(encoded) > MAX_BYTES: raise RecoveryError('Recovery content exceeds its size limit.')
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            temporary = None
            try:
                descriptor, temporary = tempfile.mkstemp(prefix='.session-', dir=self.path.parent)
                with os.fdopen(descriptor, 'wb') as handle:
                    handle.write(encoded); handle.flush(); os.fsync(handle.fileno())
                os.replace(temporary, self.path)
            except OSError:
                raise RecoveryError('Session checkpoint could not be saved; the previous file was retained.') from None
            finally:
                if temporary and os.path.exists(temporary):
                    try: os.unlink(temporary)
                    except OSError: pass
            self._signature = self._stat()
            self.record, self.revision, self.error = value, hashlib.sha256(encoded).hexdigest()[:32], ''
            return True
