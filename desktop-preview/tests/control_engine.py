"""Real confirmation/delivery code, mocked lifecycle/devices; no live services."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import queue
import sys
import threading
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--directory', required=True)
parser.add_argument('--settings', action='store_true')
args = parser.parse_args()
os.environ['VERSEVIEW_OBSERVER'] = '1'
os.environ['VERSEVIEW_OBSERVER_DIRECTORY'] = args.directory
repository = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(repository), str(repository / 'tests')]
from test_delivery import DeliveryTests, engine
from desktop_control import DesktopControl
import observer_feed

case = DeliveryTests()
case.setUp()
state = 'stopped'
config = {'streams': {'primary': {'enabled': True, 'language': 'en', 'provider': 'deepgram'},
                      'secondary': {'enabled': True, 'language': 'ml', 'provider': 'sarvam'}},
          'bible_translation': 'KJV'}
observer_feed.begin(config, origin='callback-replay')
engine.PRIMARY_LANGUAGE, engine.SECONDARY_LANGUAGE = 'en', 'ml'
engine.PRIMARY_PARSER, engine.SECONDARY_PARSER = engine.parse_eng, engine.parse_ml
engine._verse_watcher = None
commands = queue.Queue()
settings_case = None
fail_save = False
settings_adapter = None
if args.settings:
    from test_desktop_settings import SettingsTests
    from desktop_settings import DesktopSettings, LANGUAGES
    import settings as settings_config
    settings_case = SettingsTests()
    settings_case.test_directory = args.directory
    settings_case.setUp()
    def apply_settings(changes, storage):
        global fail_save
        if fail_save:
            fail_save = False
            with patch.object(settings_config, 'save', return_value=False):
                return settings_case.binding.apply(changes, storage)
        return settings_case.binding.apply(changes, storage)
    settings_adapter = DesktopSettings(settings_case.binding.read, apply_settings)



def start():
    global state
    state = 'running'
    if settings_case:
        settings_case.gui._running = True
        values = settings_case.gui._collect_settings()
        config['streams']['primary'].update(language=LANGUAGES[values['language']], provider=values['stt_engine'])
        config['streams']['secondary'].update(enabled=values['dual_stt_enabled'], language=values['secondary_language'] or 'en', provider=values['secondary_stt_engine'])
        config['bible_translation'] = values['bible_translation']
    engine._shutdown_flag.clear()
    observer_feed.begin(config, origin='callback-replay')
    observer_feed.emit('state', state='mock_running')
    return True


def stop():
    global state
    state = 'stopped'
    if settings_case: settings_case.gui._running = False
    engine._shutdown_flag.set()
    case.ctrl.cleanup()
    observer_feed.emit('state', state='stopped')


def read_commands():
    for line in sys.stdin:
        commands.put(line.strip())
    commands.put('finish')


broker = DesktopControl(observer_feed._publisher, lambda: state, start, stop, enabled=True, settings=settings_adapter)
engine.CONFIRM_REQUEST_CALLBACK = lambda *args: broker.confirm(*args, cancelled=lambda: state != 'running')
threading.Thread(target=read_commands, daemon=True).start()
observer_feed._publisher.flush()
print(json.dumps({'ready': True, 'pid': os.getpid()}), flush=True)
try:
    while True:
        try:
            message = commands.get(timeout=.05)
        except queue.Empty:
            message = None
        if message == 'finish':
            break
        if message == 'external' and settings_case:
            settings_case.gui.bible_var.set('ASV')
        if message == 'fail-save':
            fail_save = True
            print(json.dumps({'event': 'fail-save-ready'}), flush=True)
        if message == 'diagnostic-burst':
            for n in range(80):
                observer_feed.emit('delivery',event=dict(candidate_id=f'QA-DIAGNOSTIC-{n}',reference=f'John 3:{n%36+1}',stream='primary',language='en',source='SYNTHETIC-UI-FIXTURE',stage='ui_stress',outcome='SUPPRESSED',timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),reason='Synthetic scrolling evidence; no presentation command.'))
        if message and message.startswith('noise:'):
            observer_feed.emit('transcript',stream='primary',language='en',text='Continuous synthetic UI transcript '+message.split(':',1)[1],is_final=True)
        if message == 'noise':
            observer_feed.emit('transcript', stream='primary', text='Isolated settings check', is_final=True)
        if message == 'remote-fail':
            for attempt in range(1,6):
                observer_feed.emit('remote_connection',status='connecting',attempt=attempt)
                observer_feed.emit('remote_connection',status='retrying' if attempt<5 else 'failed',attempt=attempt,reason='remote')
        if message == 'hold':
            case.ctrl.send_verse('John 3:18', confidence=.2, source='CONTROL-REPLAY', stream='secondary')
        if message == 'reject':
            case.ctrl.send_verse('John 3:19', confidence=.2, source='CONTROL-REPLAY', stream='primary')
        if message == 'speech':
            handler = engine.create_transcript_handler(case.ctrl, False, '[CONTROL-REPLAY]', engine.parse_eng)
            with patch.object(engine.time, 'time', return_value=1008):
                handler('John 3:20', True)
        broker.tick()
finally:
    broker.close()
    case.tearDown()
    case.doCleanups()
    if settings_case: settings_case.doCleanups()
    observer_feed._publisher.close()
