"""Opt-in, same-user command inbox for the desktop dashboard (no network server).

Only the GUI thread calls tick(). Confirmation workers wait for an exact candidate
answer; existing engine guards still own delivery. No command is retried.
"""
import datetime as dt
import json
from itertools import islice
import os
from pathlib import Path
import re
import threading
import uuid
from desktop_settings import SettingsError
from desktop_recovery import RecoveryError
from desktop_outline import OutlineError
from desktop_bot import BotError
from desktop_sync import SyncError

_HEX = re.compile(r"^[a-f0-9]{32}$")


def now_seconds():
    return dt.datetime.now(dt.timezone.utc).timestamp()


class DesktopControl:
    def __init__(self, publisher, state, start, stop, *, enabled=False, clock=now_seconds, settings=None, panic=None, recovery=None, suggestions=None, outline=None, bot=None, sync=None):
        self.publisher, self.state = publisher, state
        self.start, self.stop, self.enabled, self.clock = start, stop, enabled, clock
        self.settings, self.panic = settings, panic
        self.recovery = recovery
        self.suggestions = suggestions
        self.outline = outline
        self.bot = bot
        self.sync = sync
        self.control_id = uuid.uuid4().hex
        self.directory = publisher.directory / f"control-{os.getpid()}-{self.control_id}"
        self.session_id = None
        self.results, self.pending, self.seen = [], {}, set()
        self.lock = threading.RLock()
        self.closed = False
        if enabled:
            if not publisher.enabled:
                raise ValueError("Desktop control requires the observer export")
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=False)
            self.refresh()

    def refresh(self):
        if not self.enabled:
            return
        with self.lock:
            snapshot = self.publisher.snapshot()
            if not snapshot:
                return
            session_id = snapshot['session_id']
            if self.session_id != session_id:
                self._cancel_pending()
                self.session_id = session_id
            state = 'closed' if self.closed else self.state()
            actions = ['start'] if state == 'stopped' else ['stop'] if state == 'running' else []
            recovery = self.recovery.snapshot() if self.recovery else None
            if state == 'stopped' and recovery and recovery['status'] in ('available', 'staged', 'invalid'):
                if recovery['status'] != 'staged': actions.remove('start')
                actions.append('discard_session')
                if recovery['status'] == 'available': actions.append('restore_session')
            if state == 'running' and self.panic:
                actions.append('panic')
            suggestions = self.suggestions.snapshot() if self.suggestions else None
            if state == 'running' and suggestions and suggestions['active'] and not suggestions['busy']:
                actions.append('send_suggestion')
            settings = self.settings.snapshot() if self.settings else None
            if state == 'stopped' and settings:
                actions.append('save_settings')
            if state in ('stopped', 'running') and self.outline:
                actions.append('edit_outline')
            bot=self.bot.snapshot() if self.bot else None
            if state!='closed' and bot:
                if bot['status'] in ('stopped','failed') and bot['configured']:actions.append('start_bot')
                if bot['status'] in ('starting','online'):actions.append('stop_bot')
            sync=self.sync.snapshot() if self.sync else None
            if sync and sync['busy']:actions=[action for action in actions if action not in ('start','start_bot','save_settings')]
            if sync and sync['configured'] and not sync['busy'] and state=='stopped' and (not bot or bot['status'] in ('stopped','failed')):
                actions.append('pull_settings')
            self.publisher.emit('control', value={
                'id': self.control_id, 'state': state, 'actions': actions, 'settings': settings, 'recovery': recovery, 'suggestions': suggestions,
                'outline': self.outline.snapshot() if self.outline else None,
                'bot': bot,
                'sync': sync,
                'pending': [{key: item[key] for key in ('candidate_id', 'reference', 'confidence', 'stream', 'source')}
                            for item in self.pending.values()], 'results': self.results[-32:]})

    def _cancel_pending(self):
        for item in self.pending.values():
            item['answer'] = False
            item['event'].set()
        self.pending.clear()

    def confirm(self, ref, confidence, candidate_id, source, stream, cancelled=lambda: False):
        with self.lock:
            self.refresh()
            if not self.enabled or self.closed or self.state() != 'running' or len(self.pending) >= 16 or candidate_id in self.pending:
                return False
            item = dict(candidate_id=candidate_id, reference=ref, confidence=confidence,
                        source=source, stream=stream, event=threading.Event(), answer=False)
            self.pending[candidate_id] = item
            self.refresh()
        try:
            while not item['event'].wait(.1):
                if cancelled():
                    return False
            return item['answer'] and not cancelled()
        finally:
            with self.lock:
                if self.pending.get(candidate_id) is item:
                    self.pending.pop(candidate_id)
                self.refresh()

    def execute(self, request):
        """Validate at execution time, on the GUI thread. Return a scheduling result."""
        with self.lock:
            self.refresh()
            command_id = request.get('id')
            if not isinstance(command_id, str) or not _HEX.fullmatch(command_id):
                return
            if command_id in self.seen:
                return
            # Bounded session ledger. Once full, reject new work until app restart.
            if len(self.seen) >= 4096:
                return
            self.seen.add(command_id)
            action = request.get('action')
            outcome = 'rejected'
            reason = 'Invalid, expired, or stale command'
            created = request.get('created_at')
            valid = (set(request) <= {'id', 'control_id', 'session_id', 'created_at', 'action', 'candidate_id', 'settings_revision', 'changes', 'recovery_revision', 'suggestion_id', 'outline_revision', 'outline_text'}
                     and request.get('control_id') == self.control_id
                     and request.get('session_id') == self.session_id
                     and isinstance(created, (float, int)) and not isinstance(created, bool)
                     and 0 <= self.clock() - created <= 10 and self.enabled and not self.closed)
            if valid:
                try:
                    state = self.state()
                    if action=='pull_settings' and self.sync and action in self.publisher.snapshot()['control']['actions']:
                        self.sync.start();outcome,reason='requested','Credential pull requested; observe settings sync status.'
                    elif action in ('start_bot','stop_bot') and self.bot and action in self.publisher.snapshot()['control']['actions']:
                        (self.bot.start if action=='start_bot' else self.bot.stop)()
                        outcome,reason='requested','Bot lifecycle requested; observe its status. Recognition is unchanged.'
                    elif action == 'start' and state == 'stopped':
                        outcome = 'requested' if 'start' in self.publisher.snapshot()['control']['actions'] and self.start() else 'failed'
                        reason = 'Start requested; observe engine status' if outcome == 'requested' else 'Start did not begin; check the detector'
                    elif (action in ('restore_session', 'discard_session') and state == 'stopped' and self.recovery
                          and action in self.publisher.snapshot()['control']['actions']):
                        self.recovery.choose(request.get('recovery_revision'), action == 'restore_session')
                        outcome = 'prepared' if action == 'restore_session' else 'discarded'
                        reason = 'Saved context prepared. Press Start to resume; nothing was presented.' if action == 'restore_session' else 'Recovery checkpoint discarded. Recognition remains stopped.'
                    elif action == 'panic' and state == 'running' and self.panic:
                        self.panic()
                        outcome, reason = 'requested', 'Clear command requested; verify the visible output.'
                    elif action == 'send_suggestion' and state == 'running' and self.suggestions:
                        suggestion_id = request.get('suggestion_id')
                        if not isinstance(suggestion_id, str) or not _HEX.fullmatch(suggestion_id):
                            raise ValueError('Invalid suggestion identity')
                        self.suggestions.send(suggestion_id)
                        outcome, reason = 'requested', 'Suggestion send requested; inspect delivery activity for acceptance or guards.'
                    elif action == 'edit_outline' and state in ('stopped', 'running') and self.outline:
                        self.outline.edit(request.get('outline_revision'), request.get('outline_text'))
                        outcome, reason = 'saved', 'Outline notes updated. Display output changes only in a window you explicitly opened.'
                    elif action == 'save_settings' and state == 'stopped' and self.settings and action in self.publisher.snapshot()['control']['actions']:
                        self.settings.save(request.get('settings_revision'), request.get('changes'))
                        outcome, reason = 'saved', 'Settings saved. They apply when you next start the engine.'
                    elif action == 'stop' and state == 'running':
                        self._cancel_pending()
                        self.stop()
                        outcome, reason = 'requested', 'Stop requested; observe engine status'
                    elif action in ('approve', 'reject') and state == 'running':
                        item = self.pending.pop(request.get('candidate_id'), None)
                        if item and not item['event'].is_set():
                            item['answer'] = action == 'approve'
                            item['event'].set()
                            outcome, reason = 'answered', 'Decision returned to the existing engine confirmation gate'
                        else:
                            reason = 'Candidate is no longer awaiting approval'
                    else:
                        reason = 'Action unavailable in the current engine state'
                except (SettingsError, RecoveryError, OutlineError, BotError, SyncError) as exc:
                    outcome, reason = 'rejected', str(exc)
                except Exception:
                    outcome, reason = 'failed', 'Detector control failed; inspect the detector log'
            self.results.append(dict(id=command_id, action=action if action in ('start', 'stop', 'approve', 'reject', 'save_settings', 'panic', 'restore_session', 'discard_session', 'send_suggestion', 'edit_outline', 'start_bot', 'stop_bot', 'pull_settings') else 'unknown',
                                     outcome=outcome, reason=reason))
            self.results = self.results[-32:]
            self.refresh()

    def tick(self):
        if not self.enabled or self.closed:
            return
        if self.settings:
            self.settings.refresh()
        self.refresh()
        for path in islice(self.directory.glob('command-*.json'), 16):
            try:
                if path.is_symlink() or not re.fullmatch(r'command-[a-f0-9]{32}\.json', path.name):
                    continue
                with path.open('rb') as handle:
                    data = handle.read(16385)
                if len(data) <= 16384:
                    request = json.loads(data)
                    if isinstance(request, dict) and path.name == f"command-{request.get('id')}.json":
                        self.execute(request)
            except (OSError, ValueError, TypeError):
                pass
            finally:
                path.unlink(missing_ok=True)

    def close(self):
        with self.lock:
            self.closed = True
            self._cancel_pending()
            self.refresh()
        # Remove only this host's private inbox, never another process's files.
        if self.enabled:
            for path in self.directory.glob('*'):
                if path.is_file() or path.is_symlink():
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        pass
            try:
                self.directory.rmdir()
            except OSError:
                pass
