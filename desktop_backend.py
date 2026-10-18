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
        values, revision = self.load()
        if revision != expected_storage:
            raise SettingsError('Settings changed elsewhere. Reload before saving.')
        values.update(changes)
        values['bible_translation'] = values['bible_translation'].lower()
        if not self.config.save(values):
            raise SettingsError('Could not save backend settings; previous values retained.')


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
                  confirm_request_callback=confirm, gui_app=None, bot_bridge_enabled=False)
    return result


def start_problem(values):
    # Keep unsupported settings intact and make their limitations explicit.
    unsupported = [('live_points_llm_enabled', 'live outline display'),
                   ('discord_bot_token', 'Discord bot'),
                   ('settings_sync_url', 'settings sync')]
    active = [name for key, name in unsupported if values.get(key)]
    if active:
        return 'Standalone migration still needs: ' + ', '.join(active) + '. Settings were retained; use the current detector for these features.'
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

    def state(self):
        if not self.thread or not self.thread.is_alive(): return 'stopped'
        if self.stop_requested.is_set(): return 'stopping'
        snapshot = self.publisher.snapshot() or {}
        return 'running' if snapshot.get('engine_state') == 'running' else 'starting'

    def start(self, values, config, confirm):
        if self.state() != 'stopped': return False
        restored = self.recovery.for_start()
        problem = start_problem(values)
        if problem: raise BackendError(problem)
        self.error = ''
        self.stop_requested.clear()
        if self.recovery.fresh_start:
            self.engine.clear_sermon_buffer()
            self.engine.full_sermon_transcript_secondary = ''
        mapped = configuration(values, config, self.engine, confirm)
        if hasattr(self, 'suggestions'):
            mapped['watcher_suggestion_callback'] = self.suggestions.prepare(values.get('watcher_enabled'))
        self.engine.configure(**mapped)
        if restored:
            # configure resets anchor/quarantine and the secondary buffer.
            # Restore after it, before any recognition tasks can be launched.
            self.engine.restore_session_snapshot(restored)
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
        self.warmup.cancel()
        self.suggestions.cancel()
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self._signal_stop)

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
                with isolated_engine(self.engine): self.loop.run_until_complete(self._main(values))
            else:
                self.loop.run_until_complete(self._main(values))
            self.warmup.cancel()
            self.suggestions.cancel()
            self.stop_requested.set()
            self.checkpoint('stopped')
            if not self.verification:
                self._save_session(values)
        except Exception:
            self.warmup.cancel()
            self.suggestions.cancel()
            self.checkpoint('error')
            logging.getLogger(__name__).exception('Backend engine or session processing failed')
            self.error = 'Engine or session processing failed. Inspect the private backend log.'
            self.publisher.emit('state', state='error')
        finally:
            self.stop_requested.set()
            self.suggestions.cancel()
            self.suggestions.join()
            pending = asyncio.all_tasks(self.loop)
            for task in pending: task.cancel()
            if pending: self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self.loop.close()
            self.loop = None

    def checkpoint(self, reason):
        if not self.has_started: return
        try:
            with self.recovery.lock:
                if reason == 'autosave' and self.stop_requested.is_set(): return
                snapshot = self.engine.get_session_snapshot()
                snapshot['stream_languages'] = {'primary': self.engine.PRIMARY_LANGUAGE,
                                                'secondary': self.engine.SECONDARY_LANGUAGE}
                feed = self.publisher.snapshot() or {}
                snapshot['raw_preview'] = {role: '\n'.join(row['text'] for row in feed.get('transcripts', [])
                    if row['stream'] == role and row['is_final'])[-2000:] for role in ('primary', 'secondary')}
                self.recovery.save(snapshot, reason)
        except Exception:
            logging.getLogger(__name__).exception('Session recovery checkpoint failed')
            self.recovery.error = 'Session checkpoint could not be saved. Inspect the private backend log.'

    def autosave(self):
        if self.state() in ('starting', 'running') and time.monotonic() >= self.checkpoint_due:
            self.checkpoint_due = time.monotonic() + 15
            self.checkpoint('autosave')

    def _save_session(self, values):
        transcript = self.engine.full_sermon_transcript or ''
        if not transcript.strip(): return
        directory = self.profile / 'Sessions'
        directory.mkdir(mode=0o700, exist_ok=True)
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        target = directory / (stamp + '.txt')
        with target.open('x', encoding='utf-8', opener=lambda path, flags: os.open(path, flags, 0o600)) as handle:
            handle.write(transcript)
        if values.get('auto_save_notes') and len(transcript.strip()) > 100:
            summary = self.engine.generate_sermon_summary()
            with (directory / (stamp + '-summary.txt')).open('x', encoding='utf-8', opener=lambda path, flags: os.open(path, flags, 0o600)) as handle:
                handle.write(summary)


class BackendHost:
    def __init__(self, config, publisher, runtime, devices, clock=None):
        from desktop_control import DesktopControl
        from desktop_settings import DesktopSettings
        self.config, self.publisher, self.runtime = config, publisher, runtime
        self.closing = False
        self.notice = 'Recognition is stopped. Saved auto-start is not activated in this preview.'
        self.devices = devices
        self.clock = clock
        self.store = ProfileStore(config, self.state, lambda: self.devices)
        self.settings = DesktopSettings(self.store.read, self.store.apply)
        self.publisher.begin({'streams': {}}, origin='callback-replay' if runtime.verification else 'engine')
        self.control = DesktopControl(publisher, self.state, self.start, runtime.stop, enabled=True, settings=self.settings,
                                      panic=runtime.panic, recovery=getattr(runtime, 'recovery', None),
                                      suggestions=getattr(runtime, 'suggestions', None))

    def state(self):
        return 'closed' if self.closing else self.runtime.state()

    def start(self):
        values, _ = self.store.load()
        values, scheduled = effective_start_settings(values, self.clock() if self.clock else None)
        schedule_notice = ('Smart Schedule selected ' + scheduled +
                           (' with English secondary. ' if scheduled != 'English' else ' only. ')) if scheduled else ''
        try:
            from desktop_settings import project, validate_changes, SettingsError
            validate_changes(project(values), project(values), self.devices)
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
        if hasattr(self.runtime, 'autosave'): self.runtime.autosave()
        self.control.tick()
        self.publisher.emit('host', value={'managed': True, 'notice': self.runtime.error or self.notice,
                                           'verification': self.runtime.verification,
                                           'warmup': self.runtime.warmup.snapshot() if hasattr(self.runtime, 'warmup') else None})

    def close(self):
        self.closing = True
        self.control.close()
        self.runtime.stop()
        if self.runtime.thread: self.runtime.thread.join(timeout=25)
        if self.runtime.thread and self.runtime.thread.is_alive(): return False
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
        if not host.close():
            print(json.dumps({'error': 'Backend still stopping; process retained for cleanup'}), flush=True)
            while runtime.thread and runtime.thread.is_alive(): runtime.thread.join(timeout=1)


if __name__ == '__main__':
    main()
