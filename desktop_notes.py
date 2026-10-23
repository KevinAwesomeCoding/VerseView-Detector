"""Snapshot-bound sermon notes, full-text export packets and recoverable resets."""
import copy
import datetime as dt
import hashlib
import json
import logging
import os
from pathlib import Path
import tempfile
import threading
import uuid
from desktop_recovery import MAX_BYTES, RecoveryError, meaningful
from desktop_sessions import atomic_write, read_private, content

MAX_NOTES = 100_000
KINDS = ('notes', 'transcript', 'references', 'all')


class NotesError(ValueError):
    pass


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:32]


def write_text(path, text):
    data = text.encode('utf-8')
    if len(data) > MAX_BYTES: raise NotesError('Export exceeds its size limit. Previous files were retained.')
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink(): raise NotesError('Save location is unavailable.')
    descriptor, temporary = tempfile.mkstemp(prefix='.notes-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    return hashlib.sha256(data).hexdigest()


class SessionNotes:
    def __init__(self, runtime):
        self.runtime = runtime
        self.lock = threading.RLock()
        self.worker = None
        self.generation = 0
        self.status, self.message = 'idle', ''
        self.revision = uuid.uuid4().hex
        self.result = None
        self.job = None
        self.pending_auto = None
        self.export = None
        self.review = None
        self.auto = dict(status='idle', saved_at=None, transcript_path='', notes_path='', message='')
        self.path = Path(runtime.profile) / 'Notes' / 'current.json'
        self.prepare_provider = lambda: None
        self.generator = lambda snapshot: runtime.engine.generate_sermon_summary(snapshot, notify=False, strict=True)
        try:
            if self.path.exists():
                value = json.loads(read_private(self.path))
                result = value.get('result')
                if result:
                    if not isinstance(result.get('text'), str) or len(result['text']) > MAX_NOTES: raise ValueError()
                    captured = content(result['capture'])
                    self.result = {**result, 'capture': captured}
                if value.get('status') in ('generating', 'pending'):
                    self.status, self.message = 'interrupted', 'The previous notes request was interrupted. Saved content was retained; generate again explicitly.'
                elif self.result: self.status = 'ready'
        except Exception:
            self.status, self.message = 'failed', 'Saved notes could not be read. The file was retained.'
            logging.getLogger(__name__).exception('Notes load failed')

    @property
    def busy(self):
        return bool(self.worker and self.worker.is_alive())

    def route(self):
        if self.runtime.verification: return 'Isolated QA · synthetic summary completion'
        engine = self.runtime.engine
        if not getattr(engine, 'LLM_ENABLED', True): return 'Summary AI is disabled in the saved engine settings'
        router = getattr(engine, '_free_cloud_router', None)
        if router is not None:
            route = router.config.get('routes', {}).get('summary', {})
            return 'Free profile · ' + str(route.get('provider', 'configured'))[:40] + ' / ' + str(route.get('model', 'configured'))[:100]
        if engine._local_llm_active_for('summary'):
            client = engine._local_client_for('summary')
            return 'Local LLM · ' + str(getattr(client, 'model', 'configured'))[:100]
        for name, model in [('mistral', 'mistral-large-latest'), ('cerebras', 'gpt-oss-120b'), ('groq', getattr(engine, 'GROQ_VERSE_MODEL', 'configured'))]:
            if getattr(engine, name + '_client', None): return name.capitalize() + ' · ' + str(model)[:100] + ' (existing fallback policy)'
        return 'No summary provider initialized'

    def capture(self):
        captured = content(self.runtime.operator.capture())
        return captured, digest({k: v for k, v in captured.items() if k != 'notes'})

    def _persist(self):
        atomic_write(self.path, {'schema': 1, 'status': self.status, 'result': self.result})

    def snapshot(self):
        with self.lock:
            result = self.result or {}
            return dict(revision=self.revision, status=self.status, message=self.message, busy=self.busy,
                        pending_auto=self.pending_auto is not None, route=self.route(), request=copy.deepcopy(self.job),
                        text=result.get('text', ''), source_id=result.get('source_id'), captured_at=result.get('captured_at'),
                        generated_at=result.get('generated_at'), result_route=result.get('route', ''),
                        auto=copy.deepcopy(self.auto), export=copy.deepcopy(self.export),
                        memory_review=({k: v for k, v in self.review.items() if k != 'capture'} if self.review else None))

    def generate(self, revision):
        with self.lock:
            if revision != self.revision: raise NotesError('Notes changed. Review the latest state before generating.')
            if self.busy or self.pending_auto: raise NotesError('A notes request is still finishing. No retry was made.')
            if self.runtime.state() not in ('stopped', 'running'): raise NotesError('Wait for the engine to finish changing state.')
            captured, source = self.capture()
            primary, secondary = self._texts(captured)
            if len((primary + secondary).strip()) < 100: raise NotesError('At least 100 characters of speech are needed to generate sermon notes.')
            self.prepare_provider()
            self._launch(captured, source)

    @staticmethod
    def _texts(captured):
        # A journal with a known missing/oversized row is never a complete original.
        raw = captured['data']
        if not captured.get('speech_complete', True): return raw['transcript'], raw['transcript_secondary']
        return captured['speech']['primary'] or raw['transcript'], captured['speech']['secondary'] or raw['transcript_secondary']

    def _launch(self, captured, source, auto_target=None):
        if self.result and self.result['source_id'] == source and auto_target:
            self._save_auto_notes(auto_target, self.result['text']); return
        self.runtime.operator.library.save(captured, 'notes source')
        self.generation += 1
        generation = self.generation
        primary, secondary = self._texts(captured)
        payload = dict(transcript=primary, transcript_secondary=secondary, verses_cited=list(captured['data']['verses_cited']),
                       stream_languages=dict(captured['data']['stream_languages']))
        self.status, self.message = 'generating', 'Generating notes from the captured session. Listening and Stop remain available.'
        self.job = dict(source_id=source, captured_at=stamp(), route=self.route())
        job = dict(self.job)
        self.revision = uuid.uuid4().hex
        try: self._persist()
        except Exception:
            self.status, self.message = 'failed', 'Notes request could not be saved. No provider request was started.'
            raise
        def work():
            try:
                text = self.generator(payload)
                if not isinstance(text, str) or not text.strip() or len(text) > MAX_NOTES or '\x00' in text:
                    raise NotesError('Summary response was empty or exceeded its limit.')
                with self.lock:
                    if generation != self.generation: return
                    previous = self.result
                    self.result = dict(text=text, capture=copy.deepcopy(captured), **job, generated_at=stamp())
                    self.status, self.message = 'ready', 'Notes generated from the captured session. Later speech is not included.'
                    self.revision = uuid.uuid4().hex
                    try: self._persist()
                    except Exception:
                        self.result = previous
                        raise
                    if auto_target: self._save_auto_notes(auto_target, text)
                if not self.runtime.verification:
                    try: self.runtime.engine.send_sermon_notes_to_discord(text)
                    except Exception:
                        logging.getLogger(__name__).exception('Sermon notes Discord delivery failed')
            except Exception:
                logging.getLogger(__name__).exception('Sermon notes generation failed')
                with self.lock:
                    if generation != self.generation: return
                    self.status, self.message = 'failed', 'Notes generation or saving failed. Previous notes and the session snapshot were retained; no automatic retry was made.'
                    if auto_target: self.auto.update(status='failed', message='Transcript saved; summary failed. Previous notes retained.')
                    self._persist()
        self.worker = threading.Thread(target=work, name='SermonNotes', daemon=True)
        self.worker.start()

    def cancel(self):
        with self.lock:
            self.generation += 1
            self.pending_auto = None
            self.status, self.message = 'cancelled', 'Notes cancelled. An in-flight provider call may still finish; its result will be ignored. No retry was made.'
            self.auto['status'] = 'cancelled' if self.auto['status'] in ('pending', 'generating') else self.auto['status']
            self.revision = uuid.uuid4().hex
            self._persist()

    def _save_auto_notes(self, target, text):
        write_text(target, text)
        self.auto.update(status='saved', saved_at=stamp(), notes_path=str(target), message='Transcript and sermon notes saved.')

    def on_stop(self, enabled):
        with self.lock:
            captured, source = self.capture()
            primary, secondary = self._texts(captured)
            if not (primary.strip() or secondary.strip()): return
            directory = Path(self.runtime.profile) / 'Sessions'
            name = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            target = directory / (name + '-transcript.txt')
            write_text(target, self.transcript(captured, source))
            self.auto.update(status='transcript_saved', saved_at=stamp(), transcript_path=str(target), notes_path='',
                             message='Full captured transcript saved. Automatic sermon notes are off.' if not enabled else 'Transcript saved. Summary pending.')
            if enabled:
                if len((primary + secondary).strip()) < 100:
                    self.auto.update(status='skipped', message='Transcript saved; too little speech for sermon notes.')
                else:
                    self.pending_auto = (captured, source, directory / (name + '-summary.txt'))
                    self.auto['status'] = 'pending'
                    self.tick()

    def tick(self):
        with self.lock:
            if self.pending_auto and not self.busy:
                captured, source, target = self.pending_auto
                self.pending_auto = None
                self.auto['status'] = 'generating'
                try: self._launch(captured, source, target)
                except Exception:
                    self.auto.update(status='failed', message='Transcript saved; summary could not start. No retry was made.')
                    logging.getLogger(__name__).exception('Automatic summary failed to start')

    @staticmethod
    def transcript(captured, source):
        sections = [f'VerseView Detector — captured session {source}']
        for role in ('primary', 'secondary'):
            original = captured['speech'][role]
            text = original or captured['data']['transcript' if role == 'primary' else 'transcript_secondary']
            language = captured['data']['stream_languages'][role]
            label = 'Provider speech (contains labeled transliteration)' if captured.get('speech_transliterated', {}).get(role) else 'Original speech'
            sections += [f'\n{role.upper()} · {language} · ' + (label if original else 'Engine context (may be translated)'), text or '(No speech recorded)']
        return '\n\n'.join(sections)

    @staticmethod
    def references(captured):
        return '\n'.join(captured['data']['verses_cited']) or '(No cited references)'

    def prepare_export(self, revision, kind):
        with self.lock:
            if revision != self.revision or kind not in KINDS: raise NotesError('Export selection changed. Review the latest notes first.')
            if kind in ('notes', 'all'):
                if not self.result: raise NotesError('Generate sermon notes before exporting them.')
                captured, source, text = self.result['capture'], self.result['source_id'], self.result['text']
            else:
                captured, source = self.capture(); text = ''
            if kind in ('transcript', 'all') and not captured.get('speech_complete', True):
                raise NotesError('The full original transcript journal is incomplete. A truncated transcript was not exported.')
            if kind == 'transcript': text = self.transcript(captured, source)
            elif kind == 'references': text = self.references(captured)
            elif kind == 'all': text += '\n\n' + self.transcript(captured, source) + '\n\nREFERENCES\n' + self.references(captured)
            identity = uuid.uuid4().hex
            path = Path(self.runtime.profile) / 'Exports' / (identity + '.txt')
            sha = write_text(path, text)
            previous = self.export
            self.export = dict(id=identity, kind=kind, sha256=sha, source_id=source, name='VerseView-' + kind + '-' + source[:8] + '.txt')
            if previous:
                old = path.parent / (previous['id'] + '.txt')
                if not old.is_symlink(): old.unlink(missing_ok=True)

    def prepare_clear(self):
        with self.lock:
            self._can_clear()
            captured, source = self.capture()
            self.review = dict(revision=uuid.uuid4().hex, fingerprint=self._memory_fingerprint(captured),
                               source_id=source, capture=captured,
                               scope='Save a recoverable session, then clear both speech streams, parser context, history, duplicate memory, queues, suggestions, outline and generated working notes. Saved sessions, exported files, credentials and diagnostic journals are retained. VerseVIEW output is unchanged.')

    def _memory_fingerprint(self, captured):
        recovery = self.runtime.recovery.snapshot()
        return digest([captured, self.revision, recovery['revision'], self.runtime.verses.context()['revision']])

    def _can_clear(self):
        if getattr(getattr(self.runtime,'connections',None),'busy',False):raise NotesError('Wait for connection work before clearing memory.')
        if self.runtime.state() != 'stopped' or self.busy or self.pending_auto or self.runtime.operator.snapshot()['busy']:
            raise NotesError('Stop listening and wait for saving or notes calls to finish before clearing memory.')
        bot = getattr(self.runtime, 'bot', None)
        if bot and bot.snapshot()['status'] not in ('stopped', 'failed'):
            raise NotesError('Stop the remote bot before clearing memory.')

    def clear_memory(self, revision):
        with self.lock:
            self._can_clear()
            captured, _ = self.capture()
            if not self.review or revision != self.review['revision'] or self._memory_fingerprint(captured) != self.review['fingerprint']:
                raise NotesError('Session changed. Review Clear Memory again before confirming.')
            self._clear_working_memory(captured, 'before memory clear')

    def new_session(self):
        """Save the current working session, then prepare a blank listening session."""
        with self.lock:
            self._can_clear()
            if self.runtime.recovery.snapshot()['status'] == 'invalid':
                raise NotesError('The saved recovery file is unreadable. Choose Start new in Saved sessions first.')
            captured, _ = self.capture()
            self._clear_working_memory(captured, 'before new session')

    def _clear_working_memory(self, captured, reason):
        has_content = meaningful(captured['data']) or captured['outline'].strip() or any(captured['speech'].values()) or captured['notes'].strip()
        saved = self.runtime.operator.library.save(captured, reason) if has_content or reason != 'before new session' else None
        # Any checkpoint filesystem failure occurs before working memory changes.
        if saved: atomic_write(Path(self.runtime.profile) / 'Diagnostics' / ('before-clear-' + saved['id'] + '.json'), self.runtime.publisher.snapshot() or {})
        self.runtime.recovery.reset_empty()
        self.runtime.engine.reset_desktop_memory()
        self.runtime.suggestions.prepare(False)
        self.runtime.outline.cancel()
        outline = self.runtime.outline.snapshot()
        self.runtime.outline.edit(outline['revision'], '')
        self.runtime.verses.reset_context()
        self.runtime.verses.selected = self.runtime.verses.chapter = self.runtime.verses.last_send = None
        self.runtime.operator.speech_before = dict(primary='', secondary='')
        self.runtime.operator.speech_transliterated_before = dict(primary=False, secondary=False)
        self.runtime.operator.pending_restore = None
        self.result = self.job = self.review = self.export = None
        self.generation += 1
        self.status, self.message = 'idle', ('New session ready. Press Start listening. Previous session is in Saved sessions.' if reason == 'before new session' and saved else 'New session ready. Press Start listening.' if reason == 'before new session' else 'Working memory cleared. Recoverable backup is in Saved sessions.')
        self.revision = uuid.uuid4().hex
        try: self._persist()
        except Exception:
            self.message = 'Working memory cleared; notes status could not be saved. Restore the backup from Saved sessions if needed.'
            logging.getLogger(__name__).exception('Cleared notes status could not be persisted')
        self.runtime.has_started = False
        self.runtime.publisher.flush()
        feed = self.runtime.publisher.snapshot() or {}
        self.runtime.publisher.begin(feed.get('config', {'streams': {}}), origin='callback-replay' if self.runtime.verification else 'engine')
        self.runtime.operator.saved = saved
        self.runtime.operator.status, self.runtime.operator.message = 'saved', self.message

    def restore(self, text, captured):
        with self.lock:
            if self.busy: raise NotesError('Wait for the notes call to finish before restoring.')
            safe = content(captured)
            self.result = dict(text=text, capture=safe, source_id=digest({k:v for k,v in safe.items() if k != 'notes'}), captured_at=stamp(), generated_at=None, route='Restored saved notes') if text else None
            self.status, self.message = 'ready' if text else 'idle', 'Saved session notes restored.' if text else ''
            self.revision = uuid.uuid4().hex
            self._persist()
