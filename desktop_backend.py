"""Managed headless companion. Launching the host never starts recognition.

The explicit --verify-isolated mode uses the real engine with mocked services;
its snapshots are labelled callback-replay and it requires a private QA profile.
"""
import argparse
import atexit
import asyncio
import datetime as dt
import hashlib
import inspect
import json
import logging
import os
from pathlib import Path
import queue
import signal
import sys
import threading
import time
from service_schedule import effective_start_settings
from desktop_recovery import SessionRecovery, RecoveryError
from desktop_warmup import SessionWarmup
from desktop_suggestions import WatcherInbox
from desktop_outline import SessionOutline


class BackendError(ValueError):
    pass


class ProfileLock:
    """OS-released lock prevents two owned hosts using one profile concurrently."""
    def __init__(self, profile):
        self.handle = (Path(profile) / 'backend.lock').open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                self.handle.seek(0, 2)
                if not self.handle.tell(): self.handle.write(b'0'); self.handle.flush()
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            raise BackendError('This backend profile is already in use.') from None
    def close(self):
        if not self.handle.closed: self.handle.close()


class ProfileStore:
    def __init__(self, config, state, devices):
        self.config, self.state, self.devices = config, state, devices

    def load(self):
        path = self.config._settings_path()
        data = path.read_bytes() if path.exists() else b'{}'
        value = json.loads(data)
        if not isinstance(value, dict):
            raise BackendError('Backend settings are invalid.')
        return {**self.config.DEFAULTS, **value}, hashlib.sha256(data).hexdigest()

    def read(self):
        values, revision = self.load()
        return dict(values=values, storage_revision=revision, devices=self.devices())

    def apply(self, changes, expected_storage):
        from desktop_settings import SettingsError
        if self.state() != 'stopped':
            raise SettingsError('Stop the engine before changing settings.')
        if getattr(self,'blocked',lambda:False)():
            raise SettingsError('Wait for settings sync before saving settings.')
        values, revision = self.load()
        if revision != expected_storage:
            raise SettingsError('Settings changed elsewhere. Reload before saving.')
        values.update(changes)
        values['bible_translation'] = values['bible_translation'].lower()
        if not self.config.save(values):
            raise SettingsError('Could not save backend settings; previous values retained.')

    def apply_import(self,changes,credential,expected_storage):
        return self.apply_sync(changes,credential,expected_storage,imported=True)

    def apply_sync(self,changes,credential,expected_storage,*,imported=False):
        from desktop_sync import SyncError,SyncConflict
        import tempfile
        if self.state()!='stopped':raise SyncConflict('Engine state changed.')
        try:values,revision=self.load()
        except (OSError,ValueError):raise SyncConflict('Private settings are unavailable.') from None
        if revision!=expected_storage:raise SyncConflict('Private settings changed.')
        allowed=self.config.SYNC_ALLOWED_KEYS
        if imported:
            from desktop_settings import FIELDS
            from desktop_options import SECRETS
            from desktop_cloud_settings import CREDENTIALS
            allowed=allowed|FIELDS|set(SECRETS)|set(CREDENTIALS)
        if not set(changes)<=allowed:raise SyncError('Unsupported settings fields.')
        merged={**values,**changes};created=None
        try:
            if credential is not None:
                if not self.config.validate_service_account_text(credential):raise SyncError('Invalid Google credentials.')
                data=credential.encode('utf-8');directory=self.config.get_managed_gcp_credentials_dir()
                if directory.is_symlink():raise SyncError('Managed credential directory is unavailable.')
                directory.mkdir(mode=0o700,parents=True,exist_ok=True)
                target=directory/('sync-'+hashlib.sha256(data).hexdigest()+'.json')
                if target.exists() or target.is_symlink():
                    if target.is_symlink() or target.stat().st_size!=len(data) or target.read_bytes()!=data:raise SyncError('Managed credential file conflicts with downloaded content.')
                else:
                    temporary=None
                    try:
                        with tempfile.NamedTemporaryFile(dir=directory,prefix='.sync-',delete=False) as handle:
                            temporary=handle.name;handle.write(data);handle.flush();os.fsync(handle.fileno())
                        os.replace(temporary,target);created=target
                    finally:
                        if temporary:Path(temporary).unlink(missing_ok=True)
                merged['gcp_credentials_path']=str(target)
            count=sum(1 for key,value in merged.items() if values.get(key)!=value)
            if count and not self.config.save(merged):raise SyncError('Private settings save failed.')
            return count
        except Exception:
            if created:created.unlink(missing_ok=True)
            raise


def configuration(values, config, engine, confirm):
    """Map persisted values to the existing configure signature; do not reset guards."""
    from desktop_settings import LANGUAGES, project
    values = {**values, **project(values)}
    parameters = inspect.signature(engine.configure).parameters
    result = {key: values[key] for key in parameters if key in values}
    result.update(language=LANGUAGES.get(values.get('language'), 'en'),
                  bible_translation=values.get('bible_translation', 'KJV').lower(),
                  local_llm_endpoint=config.resolve_local_llm_endpoint(values),
                  gcp_credentials_path=config.resolve_gcp_credentials_path(values),
                  confirm_request_callback=confirm, gui_app=None, bot_bridge_enabled=False, panic_key='')
    return result


def start_problem(values):
    provider = values.get('stt_engine', 'deepgram')
    key = {'deepgram': 'deepgram_api_key', 'sarvam': 'sarvam_api_key', 'gladia': 'gladia_api_key',
           'assemblyai': 'assemblyai_api_key', 'assemblyai_pro': 'assemblyai_api_key',
           'assemblyai_multilingual': 'assemblyai_api_key'}.get(provider)
    if key and not values.get(key):
        return 'Provider credentials are missing. Configure them in the private backend settings file.'
    if values.get('dual_stt_enabled'):
        secondary = {**values, 'dual_stt_enabled': False, 'stt_engine': values.get('secondary_stt_engine', 'deepgram')}
        return start_problem(secondary)
    return ''


class EngineRuntime:
    def __init__(self, publisher, profile, verification=False):
        import vv_streaming_master as engine
        self.engine, self.publisher, self.profile = engine, publisher, profile
        self.verification = verification
        self.thread = self.loop = None
        self.stop_requested = threading.Event()
        self.error = ''
        self.recovery = SessionRecovery(profile)
        self.checkpoint_due = 0
        self.has_started = False
        self.warmup = SessionWarmup()
        self.suggestions = WatcherInbox(engine, lambda: self.state() == 'running')
        self.outline = SessionOutline()
        from desktop_operator import OperatorTools
        self.operator = OperatorTools(self)
        from desktop_verses import VerseTools
        if verification:
            from backend_verification import verification_chapter
            self.verses = VerseTools(self, lookup=verification_chapter)
        else: self.verses = VerseTools(self)
        from desktop_notes import SessionNotes
        self.notes = SessionNotes(self)
        if verification:
            from backend_verification import verification_summary
            self.notes.generator = lambda snapshot: verification_summary(self.engine, snapshot, fail=json.loads((self.profile/'settings.json').read_text()).get('qa_notes_failure') is True)

    def state(self):
        if not self.thread or not self.thread.is_alive(): return 'stopped'
        if self.stop_requested.is_set(): return 'stopping'
        snapshot = self.publisher.snapshot() or {}
        return 'running' if snapshot.get('engine_state') == 'running' else 'starting'

    def start(self, values, config, confirm):
        if self.state() != 'stopped': return False
        if hasattr(self, 'connections') and self.connections.busy: raise BackendError('Wait for the connection action to finish.')
        if hasattr(self, 'notes') and (self.notes.busy or self.notes.pending_auto): raise BackendError('Wait for the notes call to finish or cancel it before starting a new listening session.')
        restored = self.recovery.for_start()
        problem = start_problem(values)
        if problem: raise BackendError(problem)
        self.error = ''
        if hasattr(self, 'operator'): self.operator.prepare_start(self.recovery.fresh_start)
        self.stop_requested.clear()
        if self.recovery.fresh_start:
            self.engine.clear_sermon_buffer()
            self.engine.full_sermon_transcript_secondary = ''
        mapped = configuration(values, config, self.engine, confirm)
        if hasattr(self, 'suggestions'):
            mapped['watcher_require_approval'] = True
            mapped['watcher_suggestion_callback'] = self.suggestions.prepare(values.get('watcher_enabled'))
        if hasattr(self, 'outline'):
            callback, current, status = self.outline.prepare(values.get('live_points_llm_enabled'))
            mapped.update(live_points_callback=callback, live_points_get_current_cb=current,
                          live_points_status_callback=status, live_points_enabled=bool(values.get('live_points_llm_enabled')))
        self.engine.configure(**mapped)
        if hasattr(self, 'operator'): self.operator.apply_mode()
        if hasattr(self, 'outline'):
            self.outline.provider_ready = bool(self.engine.LLM_ENABLED and
                self.engine._role_has_llm('outline', self.engine.cerebras_client, self.engine.groq_client))
        if restored:
            # configure resets anchor/quarantine and the secondary buffer.
            # Restore after it, before any recognition tasks can be launched.
            self.engine.restore_session_snapshot(restored)
        if hasattr(self, 'verses'): self.verses.prepare_start()
        self.recovery.started()
        self.has_started = True
        self.checkpoint_due = time.monotonic() + 15
        self.engine.show_malayalam_raw = bool(values.get('show_malayalam_raw'))
        if self.verification:
            snapshot = self.publisher.snapshot()
            self.publisher.begin(snapshot['config'], origin='callback-replay')
        self.thread = threading.Thread(target=self._run, args=(values,), name='VerseViewEngine', daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self.stop_requested.set()
        if hasattr(self, 'verses'): self.verses.cancel()
        self.warmup.cancel()
        self.suggestions.cancel()
        self.outline.cancel()
        if self.loop and self.loop.is_running():
            try:self.loop.call_soon_threadsafe(self._signal_stop)
            except RuntimeError:pass  # The owned loop may have just completed.

    def panic(self):
        self.engine.trigger_panic()

    def _signal_stop(self):
        if self.engine.stop_event: self.engine.stop_event.set()

    async def _main(self, values):
        # Covers Stop during startup before engine.main has installed stop_event.
        self.warmup.start(self.engine, bool(values.get('local_llm_warm_at_start')),
                          stopped=self.stop_requested.is_set)
        task = asyncio.create_task(self.engine.main())
        while not task.done():
            if self.stop_requested.is_set(): self._signal_stop()
            await asyncio.wait([task], timeout=.1)
        await task

    def _run(self, values):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            if self.verification:
                from backend_verification import isolated_engine
                with isolated_engine(self.engine, silent=values.get('qa_bot_silence') is True, notes_fixture=values.get('qa_notes_fixture') is True): self.loop.run_until_complete(self._main(values))
            else:
                self.loop.run_until_complete(self._main(values))
            self.warmup.cancel()
            self.suggestions.cancel()
            self.outline.cancel()
            self.stop_requested.set()
            self.checkpoint('stopped')
            if hasattr(self, 'operator'): self.operator.normal_stop_save()
            if not (hasattr(self, 'operator') and self.operator.emergency):
                self._save_session(values)
        except Exception:
            self.warmup.cancel()
            self.suggestions.cancel()
            self.outline.cancel()
            self.checkpoint('error')
            logging.getLogger(__name__).exception('Backend engine or session processing failed')
            self.error = 'Engine or session processing failed. Inspect the private backend log.'
            self.publisher.emit('state', state='error')
        finally:
            self.stop_requested.set()
            self.suggestions.cancel()
            self.outline.cancel()
            self.suggestions.join()
            if hasattr(self,'bot'):self.bot.drain_delivery()
            if hasattr(self,'verses'):self.verses.join()
            pending = asyncio.all_tasks(self.loop)
            for task in pending: task.cancel()
            if pending: self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            # A cancelled async task can leave a synchronous model call in the
            # loop's executor. Retain Stopping until owned calls have returned.
            self.loop.run_until_complete(self.loop.shutdown_default_executor())
            self.loop.close()
            self.loop = None

    def session_snapshot(self):
        snapshot = self.engine.get_session_snapshot() if self.has_started else {}
        snapshot['stream_languages'] = {'primary': self.engine.PRIMARY_LANGUAGE, 'secondary': self.engine.SECONDARY_LANGUAGE}
        feed = self.publisher.snapshot() or {}
        snapshot['raw_preview'] = {role: '\n'.join(row['text'] for row in feed.get('transcripts', [])
            if row['stream'] == role and row['is_final'])[-2000:] for role in ('primary', 'secondary')}
        return snapshot

    def checkpoint(self, reason):
        if not self.has_started: return
        try:
            with self.recovery.lock:
                if reason == 'autosave' and self.stop_requested.is_set(): return
                snapshot = self.session_snapshot()
                self.recovery.save(snapshot, reason)
        except Exception:
            logging.getLogger(__name__).exception('Session recovery checkpoint failed')
            self.recovery.error = 'Session checkpoint could not be saved. Inspect the private backend log.'

    def autosave(self):
        if self.state() in ('starting', 'running') and time.monotonic() >= self.checkpoint_due:
            self.checkpoint_due = time.monotonic() + 15
            self.checkpoint('autosave')
            if hasattr(self, 'operator') and not self.operator.snapshot()['busy']:
                self.operator.save(autosave=True)

    def _save_session(self, values):
        if hasattr(self, 'notes'):
            try: self.notes.on_stop(bool(values.get('auto_save_notes')))
            except Exception:
                self.notes.auto.update(status='failed', message='Transcript export could not be saved. Session-library and recovery saves are separate; check their status. No summary request was started.')
                logging.getLogger(__name__).exception('Stopped session transcript export failed')



class BackendHost:
    def __init__(self, config, publisher, runtime, devices, clock=None):
        from desktop_control import DesktopControl
        from desktop_settings import DesktopSettings
        self.config, self.publisher, self.runtime = config, publisher, runtime
        self.closing = False
        self.notice = 'Recognition is stopped. Automatic listening requires this computer’s explicit startup preference.'
        self.devices = devices
        self.clock = clock
        self.store = ProfileStore(config, self.state, lambda: self.devices)
        self.settings = DesktopSettings(self.store.read, self.store.apply)
        if hasattr(runtime, 'notes'): runtime.notes.prepare_provider = self.prepare_notes_provider
        if hasattr(runtime, 'verses'): runtime.verses.translation = lambda: self.store.load()[0].get('bible_translation', 'kjv')
        from desktop_bot import DesktopBot
        self.bot = DesktopBot(runtime,self.store.load)
        runtime.bot = self.bot
        from desktop_sync import SettingsSync
        sync_options={}
        if runtime.verification:
            from backend_verification import verification_download
            sync_options['fetch']=verification_download
        self.sync=SettingsSync(config,self.store.load,self.store.apply_sync,self.sync_ready,**sync_options)
        from desktop_connections import Connections
        runtime.connections=Connections(runtime,self.store,self.settings)
        self.store.blocked=lambda:self.sync.busy or runtime.connections.busy
        self.sync.auto_start()
        self.publisher.begin({'streams': {}}, origin='callback-replay' if runtime.verification else 'engine')
        self.control = DesktopControl(publisher, self.state, self.start, runtime.stop, enabled=True, settings=self.settings,
                                      panic=runtime.panic, recovery=getattr(runtime, 'recovery', None),
                                      suggestions=getattr(runtime, 'suggestions', None), outline=getattr(runtime, 'outline', None),bot=self.bot,sync=self.sync,operator=getattr(runtime,'operator',None),verses=getattr(runtime,'verses',None), notes=getattr(runtime,'notes',None), connections=runtime.connections,
                                      engine=runtime.engine, preference_path=runtime.profile/'approval-preferences.json')

    def prepare_notes_provider(self):
        # Saved-session summaries can initialize clients without opening audio or Chrome.
        # Once listening has initialized the engine, saved changes still apply on next Start.
        if self.runtime.has_started: return
        if self.runtime.state() != 'stopped' or self.sync.busy: raise BackendError('Wait for settings and engine work to finish.')
        values, _ = self.store.load()
        mapped = configuration(values, self.config, self.runtime.engine, None)
        mapped.update(watcher_enabled=False, watcher_require_approval=True, live_points_enabled=False,
                      begin_observer_session=False)
        self.runtime.engine.configure(**mapped)
        self.runtime.operator.apply_mode()

    def sync_ready(self):
        return self.state()=='stopped' and self.bot.snapshot()['status'] in ('stopped','failed')

    def state(self):
        return 'closed' if self.closing else self.runtime.state()

    def start(self):
        if self.sync.busy:
            self.notice='Wait for settings sync before starting recognition.'
            return False
        values, _ = self.store.load()
        schedule_notice = ''
        try:
            values, scheduled = effective_start_settings(values, self.clock() if self.clock else None)
            schedule_notice = ('Smart Schedule selected ' + scheduled +
                               (' with English secondary. ' if scheduled != 'English' else ' only. ')) if scheduled else ''
            from desktop_settings import project, validate_changes, SettingsError
            validate_changes(project(values), project(values), self.devices)
            if values.get('mic_index') not in {device['id'] for device in self.devices}:
                raise BackendError('The selected microphone is no longer an input device. Choose a microphone in Settings and save before starting.')
            result = self.runtime.start(values, self.config, self.confirm)
            self.notice = schedule_notice + 'Engine start requested; device/provider readiness is reported separately.'
            return result
        except (BackendError, SettingsError, RecoveryError) as exc:
            self.notice = schedule_notice + str(exc)
            return False
        except Exception:
            logging.getLogger(__name__).exception("Backend configuration failed")
            self.notice = "Could not configure the engine. Inspect the private backend log."
            return False

    def confirm(self, *args):
        return self.control.confirm(*args, cancelled=lambda: self.closing or self.runtime.stop_requested.is_set())

    def tick(self):
        self.sync.tick()
        if hasattr(self.runtime, 'autosave'): self.runtime.autosave()
        if hasattr(self.runtime, 'notes'): self.runtime.notes.tick()
        from desktop_setup import preview
        try: self.control.session_setup = preview(self.store.load()[0], self.clock() if self.clock else None, self.devices)
        except (OSError, ValueError): self.control.session_setup = dict(status='invalid', message='Settings are unavailable.')
        self.control.tick()
        cloud = (self.runtime.engine.free_cloud_status() if hasattr(getattr(self.runtime, 'engine', None), 'free_cloud_status') else {})
        cloud_notice = ' '.join(f'{role}: {state["message"]}' for role, state in cloud.items() if state['kind'] != 'ok')
        self.publisher.emit('host', value={'managed': True, 'notice': self.runtime.error or cloud_notice or self.notice,
                                           'verification': self.runtime.verification,
                                           'warmup': self.runtime.warmup.snapshot() if hasattr(self.runtime, 'warmup') else None})

    def close(self):
        self.closing = True
        self.runtime.stop()
        bot_closed=self.bot.close()
        sync_closed=self.sync.close()
        self.control.close()
        if self.runtime.thread: self.runtime.thread.join(timeout=25)
        verses = getattr(self.runtime, 'verses', None)
        if verses: verses.join()
        notes = getattr(self.runtime, 'notes', None)
        if notes:
            if notes.worker: notes.worker.join(timeout=20)
            notes.tick()
            if notes.worker: notes.worker.join(timeout=20)
            if notes.busy or notes.pending_auto: return False
        connections=getattr(self.runtime,'connections',None)
        if connections and connections.worker:
            connections.cancelled.set();connections.worker.join(timeout=2)
            if connections.busy:return False
        worker = getattr(getattr(self.runtime,'operator',None),'worker',None)
        if not bot_closed or not sync_closed or self.runtime.thread and self.runtime.thread.is_alive() or worker and worker.is_alive(): return False
        self.publisher.close()
        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', required=True)
    parser.add_argument('--verify-isolated', action='store_true')
    args = parser.parse_args()
    profile = Path(args.profile).resolve()
    if args.verify_isolated and (os.getenv('VV_PREVIEW_TEST_PROFILE') != '1' or 'QA' not in profile.parts):
        parser.error('Verification requires the explicit QA profile')
    profile.mkdir(mode=0o700, parents=True, exist_ok=True)
    lease = ProfileLock(profile)
    atexit.register(lease.close)
    os.environ['VERSEVIEW_PROFILE_DIRECTORY'] = str(profile)
    os.environ['VERSEVIEW_OBSERVER'] = '1'
    os.environ['VERSEVIEW_OBSERVER_DIRECTORY'] = str(profile / 'Observer')
    import settings as config
    import observer_feed
    shutdown = threading.Event()
    def parent_input():
        for line in sys.stdin:
            try:
                if json.loads(line) == {'action': 'shutdown'}: break
            except ValueError: pass
        shutdown.set()  # Parent pipe EOF must also stop recognition.
    threading.Thread(target=parent_input, name='BackendParent', daemon=True).start()
    for name in ('SIGTERM', 'SIGINT'):
        if hasattr(signal, name): signal.signal(getattr(signal, name), lambda *_: shutdown.set())
    runtime = EngineRuntime(observer_feed._publisher, profile, args.verify_isolated)
    if args.verify_isolated:
        devices = [{'id': 0, 'label': 'Verification microphone — no audio capture'}]
    else:
        import pyaudio
        audio = pyaudio.PyAudio()
        try:
            devices = [{'id': index, 'label': str(audio.get_device_info_by_index(index)['name'])}
                       for index in range(audio.get_device_count()) if audio.get_device_info_by_index(index).get('maxInputChannels', 0) > 0]
        finally: audio.terminate()
    clock = None
    if args.verify_isolated:
        from backend_verification import verification_time
        clock = verification_time
    host = BackendHost(config, observer_feed._publisher, runtime, devices, clock=clock)
    host.tick()
    observer_feed._publisher.flush()
    print(json.dumps({'ready': True, 'pid': os.getpid(), 'frozen': bool(getattr(sys, 'frozen', False)),
                      'verification': args.verify_isolated, 'guiImported': 'vv_gui' in sys.modules or 'tkinter' in sys.modules}), flush=True)
    try:
        while not shutdown.wait(.15): host.tick()
    finally:
        warned=False
        while not host.close():
            if not warned:
                print(json.dumps({'error': 'Backend still stopping; process retained for cleanup'}), flush=True)
                warned=True
            time.sleep(.2)


if __name__ == '__main__':
    if os.getenv('VV_RUN_BOT') == '1':
        import runpy
        runpy.run_path(str(Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'vv_discord_bot.py'),run_name='__main__')
    else:
        main()
