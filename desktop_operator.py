"""Acknowledged operator modes and AI-free session saves for the owned backend."""
import json
from pathlib import Path
import threading
import time
from desktop_sessions import SessionLibrary, atomic_write, read_private
from desktop_recovery import MAX_TEXT, RecoveryError, meaningful


class OperatorTools:
    def __init__(self, runtime):
        self.runtime = runtime
        self.library = SessionLibrary(runtime.profile)
        self.path = Path(runtime.profile) / 'operator-state.json'
        self.lock = threading.RLock()
        self.worker = None
        self.worship = False
        self.emergency = False
        self.start_after = 0
        self.status, self.message, self.saved = 'idle', '', None
        self.pending_restore = None
        self.speech_before = {'primary': '', 'secondary': ''}
        try:
            if self.path.exists():
                value = json.loads(read_private(self.path))
                if set(value) != {'schema', 'worship'} or value['schema'] != 1 or type(value['worship']) is not bool: raise ValueError()
                self.worship = value['worship']
        except (OSError, ValueError, TypeError):
            # Invalid preference fails closed for delivery; never silently starts STT.
            self.worship = True
            self.message = 'Worship is on because its saved preference could not be read. Set it explicitly to repair the preference.'
        self.apply_mode()

    def apply_mode(self):
        self.runtime.engine.set_delivery_mode(worship=self.worship, hold=self.emergency)

    def set_worship(self, enabled):
        if type(enabled) is not bool: raise RecoveryError('Invalid Worship choice.')
        with self.lock:
            atomic_write(self.path, {'schema': 1, 'worship': enabled})
            self.worship = enabled
            self.apply_mode()
            self.message = 'Worship on: speech continues; new verse delivery is blocked.' if enabled else 'Worship off: waiting for fresh input; old queued references were cancelled.'

    def snapshot(self):
        with self.lock:
            return {'worship': self.worship, 'emergency': self.emergency, 'busy': bool(self.worker and self.worker.is_alive()),
                    'status': self.status, 'message': self.message, 'saved': self.saved, 'library': self.library.snapshot()}

    def capture(self):
        raw = self.runtime.session_snapshot()
        if not self.runtime.has_started and self.runtime.recovery.record:
            raw = self.runtime.recovery.record['data']
        speech = dict(self.speech_before)
        # Flush the existing bounded journal writer before reading final originals.
        self.runtime.publisher.flush()
        feed = self.runtime.publisher.snapshot() or {}
        key = feed.get('session_id', '')
        if len(key) == 32 and all(c in '0123456789abcdef' for c in key):
            path = self.runtime.publisher.directory / ('transcript-' + key + '.jsonl')
            if path.exists():
                encoded = read_private(path)
                for line in encoded.splitlines(keepends=True):
                    if not line.endswith(b'\n'): break  # An append in progress is not a committed row.
                    row = json.loads(line)
                    role = row.get('stream')
                    if role in speech and row.get('is_final') is True and isinstance(row.get('text'), str):
                        speech[role] += ('\n' if speech[role] else '') + row['text']
                        if len(speech[role]) > MAX_TEXT: raise RecoveryError('Speech exceeds the session save limit. Previous saves retained.')
        return {'data': raw, 'outline': self.runtime.outline.snapshot()['text'], 'speech': speech}

    def prepare_start(self, fresh):
        if self.worker and self.worker.is_alive(): raise RecoveryError('Wait for session saving to finish before starting.')
        self.emergency = False
        if fresh:
            self.speech_before = {'primary': '', 'secondary': ''}
            self.pending_restore = None
        elif self.runtime.has_started and not self.pending_restore:
            self.speech_before = self.capture()['speech']
        if self.pending_restore:
            self.speech_before = dict(self.pending_restore['speech'])
            outline = self.runtime.outline.snapshot()
            self.runtime.outline.edit(outline['revision'], self.pending_restore['outline'])
            self.pending_restore = None
        self.apply_mode()

    def resume(self, record_id, revision):
        if self.runtime.state() != 'stopped' or self.snapshot()['busy']: raise RecoveryError('Stop listening and wait for saving before resuming.')
        value = self.library.restore_content(record_id, revision)
        # Preserve the current working context/checkpoint before staging a replacement.
        if self.runtime.has_started:
            current = self.capture()
            if meaningful(current['data']) or current['outline'].strip() or any(current['speech'].values()): self.library.save(current, 'before restore')
        elif self.runtime.recovery.record:
            self.library.save({'data': self.runtime.recovery.record['data']}, 'previous recovery')
        self.runtime.recovery.stage_saved(value['data'])
        self.pending_restore = value
        self.message = 'Session prepared. Press Start listening to resume; nothing was presented.'

    def save(self, emergency=False, autosave=False):
        with self.lock:
            if emergency:
                # Set the gate before stopping, before waiting for any disk or worker.
                self.emergency = True
                self.start_after = time.time()
                self.apply_mode()
                self.runtime.stop()
                if hasattr(self.runtime, 'bot'): self.runtime.bot.stop()
            previous = self.worker
            if previous and previous.is_alive() and not emergency: raise RecoveryError('A session save is already in progress.')
            if self.emergency and self.status == 'stopping' and previous and previous.is_alive(): return
            self.status = 'stopping' if emergency else 'saving'
            self.message = 'Delivery blocked. Stopping owned work before the final save…' if emergency else 'Saving session…'
            self.saved = None
            def work():
                try:
                    if previous and previous.is_alive(): previous.join()
                    if emergency:
                        if self.runtime.thread: self.runtime.thread.join()
                        if hasattr(self.runtime, 'bot'): self.runtime.bot.drain_delivery()
                    captured = self.capture()
                    if autosave and not meaningful(captured['data']) and not captured['outline'].strip() and not any(captured['speech'].values()):
                        with self.lock:
                            if self.worker is threading.current_thread(): self.status, self.message = 'idle', ''
                        return
                    saved = self.library.save(captured, 'emergency' if emergency else 'autosave' if autosave else 'manual')
                    with self.lock:
                        if self.worker is not threading.current_thread(): return
                        self.saved, self.status = saved, 'saved'
                        self.message = 'Session saved. Listening is stopped; delivery remains blocked until an explicit Start.' if emergency else 'Session saved.'
                except Exception:
                    with self.lock:
                        if self.worker is not threading.current_thread(): return
                        self.status = 'failed'
                        self.message = 'Session was not saved. Previous saves retained; inspect the private backend log.'
                    import logging
                    logging.getLogger(__name__).exception('Operator session save failed')
            self.worker = threading.Thread(target=work, name='SessionSave', daemon=True)
            self.worker.start()

    def normal_stop_save(self):
        with self.lock:
            if self.emergency: return
            previous = self.worker
        if previous and previous.is_alive(): previous.join()
        if self.emergency: return
        try:
            captured = self.capture()
            if not meaningful(captured['data']) and not captured['outline'].strip() and not any(captured['speech'].values()): return
            saved = self.library.save(captured, 'stopped')
            with self.lock: self.saved, self.status, self.message = saved, 'saved', 'Stopped session saved.'
        except Exception:
            self.status, self.message = 'failed', 'Session archive failed. Inspect the private backend log; existing saves retained.'
