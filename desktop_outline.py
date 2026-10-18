"""Session-bound outline text; model replies cannot overwrite newer operator edits."""
import datetime as dt
import threading
import uuid

MAX_TEXT = 4000


def valid_text(text):
    if not isinstance(text, str) or '\x00' in text: return False
    try: return len(text.encode('utf-16-le')) // 2 <= MAX_TEXT
    except UnicodeError: return False


class OutlineError(ValueError):
    pass


class SessionOutline:
    def __init__(self):
        self.lock = threading.RLock()
        self.generation = 0
        self.enabled = self.active = self.provider_ready = False
        self.text = self.source = self.message = ''
        self.revision = uuid.uuid4().hex
        self.updated_at = None
        self.pending_revision = None
        self.status = 'idle'

    def prepare(self, enabled):
        with self.lock:
            self.generation += 1
            generation = self.generation
            self.enabled, self.active = bool(enabled), True
            self.provider_ready = False
            self.status, self.message, self.pending_revision = 'waiting', '', None
        return (lambda text: self.receive(text, generation), lambda: self.current(generation),
                lambda status: self.model_status(status, generation))

    def current(self, generation):
        with self.lock:
            if generation != self.generation or not self.active: return ''
            self.pending_revision = self.revision
            return self.text

    def model_status(self, status, generation):
        with self.lock:
            if generation != self.generation or not self.active or not self.enabled: return
            if status == 'generating': self.status, self.message = 'generating', ''
            elif status == 'failed':
                self.status, self.message = 'error', 'Outline generation failed. Previous notes retained; inspect the private backend log.'

    def receive(self, text, generation):
        with self.lock:
            if generation != self.generation or not self.active or not self.enabled: return
            if self.pending_revision != self.revision:
                self.status, self.message = 'edited', 'A generated update was skipped because the notes changed. Your latest notes were retained.'
                return
            if not valid_text(text) or not text.strip():
                self.status, self.message = 'error', 'Generated outline was empty or exceeded the 4,000-character limit. Previous notes retained.'
                return
            self._set(text, 'model')

    def edit(self, expected_revision, text):
        with self.lock:
            if expected_revision != self.revision:
                raise OutlineError('Outline changed. Reload the latest notes before saving.')
            if not valid_text(text):
                raise OutlineError('Outline must contain at most 4,000 characters.')
            self._set(text, 'manual')

    def _set(self, text, source):
        self.text, self.source, self.message = text, source, ''
        self.status = 'edited' if source == 'manual' else 'updated'
        self.revision = uuid.uuid4().hex
        self.updated_at = dt.datetime.now(dt.timezone.utc).isoformat()

    def snapshot(self):
        with self.lock:
            return dict(revision=self.revision, text=self.text, source=self.source,
                        updated_at=self.updated_at, enabled=self.enabled, active=self.active,
                        provider_ready=self.provider_ready, status=self.status, message=self.message)

    def cancel(self):
        with self.lock:
            self.active = False
            self.pending_revision = None
            self.status = 'stopped'
