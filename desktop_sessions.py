"""Private immutable session library. Renderer requests use opaque IDs, never paths."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import uuid
from desktop_recovery import MAX_BYTES, MAX_TEXT, RecoveryError, meaningful, sermon_data
from desktop_outline import valid_text

_ID = re.compile(r'^[a-f0-9]{32}$')
PAGE_SIZE = 20
AUTOSAVE_ID = hashlib.sha256(b'verseview-current-autosave').hexdigest()[:32]


def atomic_write(path, value):
    encoded = json.dumps(value, ensure_ascii=False).encode('utf-8')
    if len(encoded) > MAX_BYTES: raise RecoveryError('Session exceeds the save limit; previous saves retained.')
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink(): raise RecoveryError('Session location is unavailable.')
    temporary = None
    try:
        descriptor, temporary = tempfile.mkstemp(prefix='.session-', dir=path.parent)
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(encoded); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError: raise RecoveryError('Session could not be saved; previous saves retained.') from None
    finally:
        if temporary and os.path.exists(temporary): os.unlink(temporary)


def read_private(path):
    if path.is_symlink() or not path.is_file(): raise RecoveryError('Saved session is unavailable.')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0))
    with os.fdopen(fd, 'rb') as handle: data = handle.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES: raise RecoveryError('Saved session exceeds the read limit.')
    return data


def content(raw):
    data = sermon_data(raw.get('data'))
    outline = raw.get('outline', '')
    if not valid_text(outline): raise RecoveryError('Saved outline is invalid.')
    speech = raw.get('speech', {})
    if not isinstance(speech, dict): raise RecoveryError('Saved speech is invalid.')
    for role in ('primary', 'secondary'):
        text = speech.get(role, '')
        if not isinstance(text, str) or len(text) > MAX_TEXT: raise RecoveryError('Saved speech exceeds its limit.')
    return {'data': data, 'outline': outline, 'speech': {role: speech.get(role, '') for role in ('primary', 'secondary')}}


class SessionLibrary:
    def __init__(self, profile):
        self.root = Path(profile)
        self.directory = self.root / 'SessionLibrary'
        self.lock = threading.RLock()
        self.page = 0
        self.selected = None
        self.rows, self.more, self.message = [], False, ''
        self.refresh()

    def _paths(self):
        # Bounded discovery; no user data is deleted for retention.
        rows = []
        for directory, suffix, kind in ((self.directory, '.json', 'session'), (self.root / 'Sessions', '.txt', 'transcript')):
            if directory.is_symlink(): continue
            if not directory.exists(): continue
            with os.scandir(directory) as entries:
                for index, entry in enumerate(entries):
                    if index >= 10000: raise RecoveryError('Session folder exceeds the catalogue limit. Existing files retained.')
                    if entry.is_symlink() or not entry.is_file(follow_symlinks=False) or not entry.name.endswith(suffix): continue
                    if kind == 'session' and entry.name != 'autosave.json' and not _ID.fullmatch(entry.name[:-5]): continue
                    key = (AUTOSAVE_ID if entry.name == 'autosave.json' else entry.name[:-5]) if kind == 'session' else hashlib.sha256(('text:' + entry.name).encode()).hexdigest()[:32]
                    rows.append((entry.stat(follow_symlinks=False).st_mtime_ns, key, Path(entry.path), kind))
        return sorted(rows, reverse=True)

    def _load(self, record_id, revision=None, paths=None):
        if not isinstance(record_id, str) or not _ID.fullmatch(record_id): raise RecoveryError('Invalid saved-session identity.')
        matches = [row for row in (self._paths() if paths is None else paths) if row[1] == record_id]
        if len(matches) != 1: raise RecoveryError('Saved session was removed or is ambiguous. Refresh the list.')
        _, _, path, kind = matches[0]
        raw = read_private(path)
        digest = hashlib.sha256(raw).hexdigest()[:32]
        if revision is not None and revision != digest: raise RecoveryError('Saved session changed. Preview it again before resuming.')
        if kind == 'transcript':
            text = raw.decode('utf-8')
            return digest, kind, {'saved_at': dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat(),
                                 'reason': 'text archive', 'data': sermon_data({}), 'speech': {'primary': text, 'secondary': ''}, 'outline': ''}
        value = json.loads(raw)
        if not isinstance(value, dict) or value.get('schema') != 1 or value.get('id') != record_id: raise RecoveryError('Saved session format is invalid.')
        saved = value.get('saved_at')
        if not isinstance(saved, str) or len(saved) > 64: raise RecoveryError('Saved time is invalid.')
        dt.datetime.fromisoformat(saved)
        return digest, kind, {**content(value), 'saved_at': saved, 'reason': str(value.get('reason', 'saved'))[:40]}

    def refresh(self, page=None):
        with self.lock:
            if page is not None:
                if type(page) is not int or not 0 <= page <= 499: raise RecoveryError('Invalid catalogue page.')
                self.page = page
            try:
                paths = self._paths(); start = self.page * PAGE_SIZE
                self.more = len(paths) > start + PAGE_SIZE; self.rows = []
                for _, key, _, kind in paths[start:start + PAGE_SIZE]:
                    try:
                        revision, kind, value = self._load(key, paths=paths)
                        self.rows.append({'id': key, 'revision': revision, 'kind': kind, 'saved_at': value['saved_at'],
                                          'reason': value['reason'], 'resumable': kind == 'session'})
                    except (OSError, ValueError, TypeError):
                        self.rows.append({'id': key, 'revision': None, 'kind': 'invalid', 'saved_at': '', 'reason': 'Unreadable; retained', 'resumable': False})
                self.message = ''
            except (OSError, ValueError): self.message = 'Session catalogue could not be read. Existing files retained.'

    def preview(self, record_id, offset=0):
        if type(offset) is not int or not 0 <= offset <= MAX_BYTES: raise RecoveryError('Invalid preview offset.')
        with self.lock:
            revision, kind, value = self._load(record_id)
            texts = {'primary': value['speech']['primary'] or value['data']['transcript'],
                     'secondary': value['speech']['secondary'] or value['data']['transcript_secondary']}
            self.selected = {'id': record_id, 'revision': revision, 'kind': kind, 'saved_at': value['saved_at'],
                             'offset': offset, 'more': any(len(text) > offset + 4000 for text in texts.values()),
                             'primary': texts['primary'][offset:offset + 4000], 'secondary': texts['secondary'][offset:offset + 4000],
                             'sources': {role: 'speech' if value['speech'][role] else 'context' for role in texts},
                             'outline': value['outline'], 'languages': value['data']['stream_languages'],
                             'references': [row['ref'] for row in value['data']['verse_history'][-20:]], 'resumable': kind == 'session'}

    def restore_content(self, record_id, revision):
        if not isinstance(revision, str) or not _ID.fullmatch(revision): raise RecoveryError('Preview the saved session before resuming.')
        with self.lock:
            _, kind, value = self._load(record_id, revision)
            if kind != 'session': raise RecoveryError('Text archives can be read but cannot restore engine context.')
            return value

    def save(self, raw, reason):
        with self.lock:
            value = content(raw)
            if not meaningful(value['data']) and not value['outline'].strip() and not any(value['speech'].values()):
                raise RecoveryError('There is no session content to save yet.')
            key = AUTOSAVE_ID if reason == 'autosave' else uuid.uuid4().hex
            record = {'schema': 1, 'id': key, 'saved_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'reason': reason, **value}
            atomic_write(self.directory / ('autosave.json' if reason == 'autosave' else key + '.json'), record)
            self.refresh(0)
            return {'id': key, 'saved_at': record['saved_at']}

    def snapshot(self):
        with self.lock:
            return {'page': self.page, 'more': self.more, 'rows': list(self.rows), 'selected': self.selected, 'message': self.message}
