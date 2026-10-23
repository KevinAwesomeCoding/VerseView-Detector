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
from desktop_verses import VerseError
from desktop_suggestions import SuggestionError
from desktop_notes import NotesError
from desktop_connections import ConnectionError

_HEX = re.compile(r"^[a-f0-9]{32}$")


def now_seconds():
    return dt.datetime.now(dt.timezone.utc).timestamp()


class DesktopControl:
    def __init__(self, publisher, state, start, stop, *, enabled=False, clock=now_seconds, settings=None, panic=None, recovery=None, suggestions=None, outline=None, bot=None, sync=None, operator=None, verses=None, notes=None, connections=None, engine=None, preference_path=None):
        self.publisher, self.state = publisher, state
        self.start, self.stop, self.enabled, self.clock = start, stop, enabled, clock
        self.settings, self.panic = settings, panic
        self.recovery = recovery
        self.suggestions = suggestions
        self.outline = outline
        self.bot = bot
        self.sync = sync
        self.operator = operator
        self.verses = verses
        self.notes = notes
        self.connections = connections
        self.engine, self.preference_path = engine, preference_path
        try: self.ask_before_sending = json.loads(preference_path.read_text()).get('ask_before_sending') is True if preference_path else False
        except (OSError, ValueError, TypeError): self.ask_before_sending = False
        if engine is not None: engine.ASK_BEFORE_SENDING = self.ask_before_sending
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
            if state in ('stopped', 'running') and self.engine is not None:
                actions.append('set_ask_before_sending')
            suggestions = self.suggestions.snapshot() if self.suggestions else None
            if state == 'running' and suggestions and suggestions['active'] and not suggestions['busy']:
                actions.extend(['send_suggestion', 'dismiss_suggestion', 'clear_suggestions'])
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
            operator = self.operator.snapshot() if self.operator else None
            if operator and state != 'closed':
                actions.extend(['list_sessions', 'preview_session'])
                if state in ('stopped', 'running'):
                    actions.append('set_worship')
                    if not operator['busy']: actions.append('save_session')
                if state == 'stopped' and not operator['busy']: actions.append('resume_saved')
                if state in ('starting', 'running', 'stopping', 'stopped') and not (operator['busy'] and operator['emergency']): actions.append('emergency_save')
                if operator['busy']: actions = [a for a in actions if a not in ('start', 'restore_session', 'discard_session')]
            verses = self.verses.snapshot() if self.verses else None
            if verses and state in ('stopped', 'running'):
                actions.append('clear_history')
                if not verses['lookup_busy']: actions.append('grid_preview')
                if not verses['lookup_busy']:
                    actions.extend(['verse_preview', 'chapter_browse'])
                    if suggestions and suggestions['active']: actions.append('preview_suggestion')
                if (not verses['send_busy'] and not (operator and operator['busy']) and (not recovery or recovery['status'] not in ('available', 'invalid'))): actions.append('set_context')
                if state == 'running' and not verses['send_busy'] and not (operator and operator['emergency']): actions.append('send_reference')
            if (verses and verses['send_busy']) or (suggestions and suggestions['busy']):
                actions = [a for a in actions if a not in ('send_reference', 'send_suggestion')]
            connections = self.connections.snapshot() if self.connections else None
            if connections and state in ('stopped','running'):
                actions.append('connection_action')
                if connections['busy']: actions=[a for a in actions if a not in ('start','resume_saved','restore_session','discard_session','save_settings','pull_settings','generate_notes','prepare_memory_clear','clear_memory','new_session')]
            notes = self.notes.snapshot() if self.notes else None
            if notes and state in ('stopped', 'running'):
                actions.append('prepare_export')
                if notes['busy'] or notes['pending_auto']:
                    actions.append('cancel_notes')
                    actions = [a for a in actions if a not in ('start','resume_saved','restore_session','discard_session','save_settings','pull_settings','new_session')]
                else:
                    actions.append('generate_notes')
                    if state == 'stopped' and not (operator and operator['busy']):
                        actions.extend(['prepare_memory_clear', 'clear_memory'])
                        if not recovery or recovery['status'] != 'invalid': actions.append('new_session')
            if connections and connections['busy']:
                actions=[a for a in actions if a not in ('start','resume_saved','restore_session','discard_session','save_settings','pull_settings','generate_notes','prepare_memory_clear','clear_memory','new_session')]
            self.publisher.emit('control', value={
                'id': self.control_id, 'state': state, 'actions': actions, 'settings': settings, 'recovery': recovery, 'suggestions': suggestions,
                'connections': connections, 'notes': notes, 'session_setup': getattr(self, 'session_setup', None), 'outline': self.outline.snapshot() if self.outline else None,
                'bot': bot, 'operator': operator, 'verses': verses,
                'sync': sync,
                'ask_before_sending': self.ask_before_sending,
                'pending': [{key: item[key] for key in ('candidate_id', 'reference', 'confidence', 'stream', 'source', 'context')}
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
                        source=source, stream=stream, context=self._candidate_context(candidate_id, stream), event=threading.Event(), answer=False)
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

    def _candidate_context(self, candidate_id, stream):
        snapshot = self.publisher.snapshot() or {}
        rows = snapshot.get('transcripts', [])
        rows = [row for row in rows if row.get('stream') == stream and row.get('text')]
        events = snapshot.get('delivery_events', [])
        transcript_id = next((event.get('transcript_id') for event in reversed(events)
                              if event.get('candidate_id') == candidate_id and event.get('transcript_id')), None)
        index = next((n for n, row in enumerate(rows) if row.get('id') == transcript_id), len(rows) - 1)
        if index < 0: return {'before': '', 'detected': '', 'after': ''}
        return {'before': str(rows[index-1]['text'])[-200:] if index else '',
                'detected': str(rows[index]['text'])[:300],
                'after': str(rows[index+1]['text'])[:200] if index+1 < len(rows) else ''}

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
            fields = {
                'connection_action': {'settings_revision','operation','role','review_id','isolated','attachment_id','include_credentials'},
                'generate_notes': {'revision'}, 'prepare_export': {'revision', 'kind'}, 'clear_memory': {'revision'},
                'approve': {'candidate_id'}, 'reject': {'candidate_id'},
                'set_ask_before_sending': {'enabled'},
                'save_settings': {'settings_revision', 'changes'},
                'restore_session': {'recovery_revision'}, 'discard_session': {'recovery_revision'},
                'grid_preview': {'reference', 'context_revision'}, 'preview_suggestion': {'suggestion_id'}, 'dismiss_suggestion': {'suggestion_id'}, 'clear_suggestions': {'revision'}, 'clear_history': {'history_revision'},
                'send_suggestion': {'suggestion_id'}, 'edit_outline': {'outline_revision', 'outline_text'},
                'list_sessions': {'page'}, 'preview_session': {'record_id', 'page'},
                'resume_saved': {'record_id', 'record_revision'}, 'set_worship': {'enabled'},
                'set_context': {'reference', 'context_revision'}, 'verse_preview': {'reference'},
                'chapter_browse': {'reference', 'page'}, 'send_reference': {'selection_id'},
            }.get(action, set())
            valid = (set(request) <= {'id', 'control_id', 'session_id', 'created_at', 'action'} | fields
                     and request.get('control_id') == self.control_id
                     and request.get('session_id') == self.session_id
                     and isinstance(created, (float, int)) and not isinstance(created, bool)
                     and 0 <= self.clock() - created <= 10 and self.enabled and not self.closed)
            if valid:
                try:
                    state = self.state()
                    if action == 'set_ask_before_sending' and self.engine is not None and state in ('stopped', 'running') and isinstance(request.get('enabled'), bool):
                        enabled = request['enabled']
                        if self.preference_path:
                            self.preference_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                            temporary = self.preference_path.with_suffix('.tmp')
                            temporary.write_text(json.dumps({'ask_before_sending': enabled}))
                            os.replace(temporary, self.preference_path)
                        self.ask_before_sending = self.engine.ASK_BEFORE_SENDING = enabled
                        if not enabled: self._cancel_pending()
                        outcome, reason = 'saved', 'Ask before sending updated.'
                    elif action=='connection_action' and self.connections and action in self.publisher.snapshot()['control']['actions']:
                        op=request.get('operation');revision=request.get('settings_revision')
                        if op=='cancel':self.connections.cancel()
                        elif op=='prepare_atem':self.connections.prepare_atem(revision)
                        elif op=='prepare_export':self.connections.prepare_export(revision,request.get('include_credentials'))
                        elif op=='import':self.connections.import_file(revision,request.get('attachment_id'),request.get('include_credentials'))
                        else:self.connections.run(op,revision,request.get('role','verse'),request.get('review_id'),request.get('isolated',False))
                        outcome,reason='requested','Connection action acknowledged. Observe its result.'
                    elif action in ('generate_notes', 'cancel_notes', 'prepare_export', 'prepare_memory_clear', 'clear_memory', 'new_session') and self.notes and action in self.publisher.snapshot()['control']['actions']:
                        if action == 'generate_notes': self.notes.generate(request.get('revision'))
                        elif action == 'cancel_notes': self.notes.cancel()
                        elif action == 'prepare_export': self.notes.prepare_export(request.get('revision'), request.get('kind'))
                        elif action == 'prepare_memory_clear': self.notes.prepare_clear()
                        elif action == 'new_session':
                            self._cancel_pending()
                            self.notes.new_session()
                        else:
                            self._cancel_pending()
                            self.notes.clear_memory(request.get('revision'))
                        outcome, reason = 'requested', 'Session request acknowledged. Observe notes, export or memory status.'
                    elif action == 'grid_preview' and self.verses and action in self.publisher.snapshot()['control']['actions']:
                        self.verses.grid_preview(request.get('context_revision'), request.get('reference'))
                        outcome, reason = 'requested', 'Read-only verse preview requested. Nothing was presented.'
                    elif action == 'clear_history' and self.verses and action in self.publisher.snapshot()['control']['actions']:
                        self.verses.clear_history(request.get('history_revision'))
                        outcome, reason = 'cleared', 'Current verse history cleared. Saved sessions and delivery diagnostics were retained.'
                    elif action in ('preview_suggestion', 'dismiss_suggestion', 'clear_suggestions') and self.suggestions and action in self.publisher.snapshot()['control']['actions']:
                        if action == 'clear_suggestions': self.suggestions.clear(request.get('revision'))
                        elif action == 'dismiss_suggestion': self.suggestions.dismiss(request.get('suggestion_id'))
                        else: self.verses.preview(self.suggestions.select(request.get('suggestion_id'))['reference'])
                        outcome, reason = 'requested', 'Suggestion request acknowledged. Preview is read-only; Display uses the delivery guards.'
                    elif action in ('set_context', 'verse_preview', 'chapter_browse', 'send_reference') and self.verses and action in self.publisher.snapshot()['control']['actions']:
                        if action == 'set_context':
                            self.verses.set_context(request.get('context_revision'), request.get('reference'))
                            self._cancel_pending()
                            outcome, reason = 'prepared', 'Context updated or staged. No presentation requested.'
                        elif action == 'send_reference':
                            self.verses.send(request.get('selection_id'))
                            outcome, reason = 'requested', 'Send requested through the delivery guards. Observe its outcome.'
                        else:
                            self.verses.preview(request.get('reference'), chapter=action == 'chapter_browse', page=request.get('page', 0))
                            outcome, reason = 'requested', 'Read-only lookup requested. Nothing was presented.'
                    elif action in ('list_sessions', 'preview_session', 'resume_saved', 'save_session', 'set_worship', 'emergency_save') and self.operator and action in self.publisher.snapshot()['control']['actions']:
                        if action == 'list_sessions': self.operator.library.refresh(request.get('page', 0))
                        elif action == 'preview_session': self.operator.library.preview(request.get('record_id'), request.get('page', 0))
                        elif action == 'resume_saved':
                            self.operator.resume(request.get('record_id'), request.get('record_revision'))
                            if self.verses: self.verses.reset_context()
                        elif action == 'set_worship':
                            self._cancel_pending()
                            self.operator.set_worship(request.get('enabled'))
                        else:
                            if action == 'emergency_save': self._cancel_pending()
                            self.operator.save(emergency=action == 'emergency_save')
                        outcome, reason = 'requested', 'Operator request accepted; observe its acknowledged state and save result.'
                    elif action=='pull_settings' and self.sync and action in self.publisher.snapshot()['control']['actions']:
                        self.sync.start();outcome,reason='requested','Credential pull requested; observe settings sync status.'
                    elif action in ('start_bot','stop_bot') and self.bot and action in self.publisher.snapshot()['control']['actions']:
                        (self.bot.start if action=='start_bot' else self.bot.stop)()
                        outcome,reason='requested','Bot lifecycle requested; observe its status. Recognition is unchanged.'
                    elif action == 'start' and state == 'stopped' and (not self.operator or created > self.operator.start_after):
                        outcome = 'requested' if 'start' in self.publisher.snapshot()['control']['actions'] and self.start() else 'failed'
                        reason = 'Start requested; observe engine status' if outcome == 'requested' else 'Start did not begin; check the detector'
                    elif (action in ('restore_session', 'discard_session') and state == 'stopped' and self.recovery
                          and action in self.publisher.snapshot()['control']['actions']):
                        if action == 'discard_session' and self.operator and self.recovery.record:
                            self.operator.library.save(self.operator.pending_restore or {'data': self.recovery.record['data']}, 'before start new')
                        self.recovery.choose(request.get('recovery_revision'), action == 'restore_session')
                        if self.verses: self.verses.reset_context()
                        outcome = 'prepared' if action == 'restore_session' else 'discarded'
                        reason = 'Saved context prepared. Press Start to resume; nothing was presented.' if action == 'restore_session' else 'Recovery checkpoint discarded. Recognition remains stopped.'
                    elif action == 'panic' and state == 'running' and self.panic:
                        self.panic()
                        outcome, reason = 'requested', 'Clear command requested; verify the visible output.'
                    elif action == 'send_suggestion' and state == 'running' and self.suggestions and action in self.publisher.snapshot()['control']['actions']:
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
                except (SettingsError, RecoveryError, OutlineError, BotError, SyncError, VerseError, SuggestionError, NotesError, ConnectionError) as exc:
                    outcome, reason = 'rejected', str(exc)
                except Exception:
                    outcome, reason = 'failed', 'Detector control failed; inspect the detector log'
            self.results.append(dict(id=command_id, action=action if action in ('set_ask_before_sending', 'start', 'stop', 'approve', 'reject', 'save_settings', 'panic', 'restore_session', 'discard_session', 'send_suggestion', 'edit_outline', 'start_bot', 'stop_bot', 'pull_settings', 'list_sessions', 'preview_session', 'resume_saved', 'save_session', 'set_worship', 'emergency_save', 'set_context', 'verse_preview', 'chapter_browse', 'send_reference', 'preview_suggestion', 'dismiss_suggestion', 'clear_suggestions', 'clear_history', 'grid_preview', 'connection_action', 'generate_notes', 'cancel_notes', 'prepare_export', 'prepare_memory_clear', 'clear_memory', 'new_session') else 'unknown',
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
