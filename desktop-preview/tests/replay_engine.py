"""Replay real engine callbacks into an isolated observer feed, never live services.

This harness deliberately bypasses microphone/STT transport and labels every
snapshot callback-replay. It reuses the production regression suite's service
isolation and fake browser controller. Nothing in the preview can control it.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--directory', required=True)
args = parser.parse_args()
os.environ['VERSEVIEW_OBSERVER'] = '1'
os.environ['VERSEVIEW_OBSERVER_DIRECTORY'] = args.directory
repository = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repository))
sys.path.insert(0, str(repository / 'tests'))
from test_delivery import DeliveryTests, engine
import observer_feed

case = DeliveryTests()
case.setUp()
release_confirmation = threading.Event()
confirmation_done = threading.Event()


def confirmation(_ref, _confidence):
    release_confirmation.wait(120)
    confirmation_done.set()
    return False


try:
    engine.PRIMARY_LANGUAGE = 'en'
    engine.SECONDARY_LANGUAGE = 'ml'
    engine.PRIMARY_PARSER = engine.parse_eng
    engine.SECONDARY_PARSER = engine.parse_ml
    engine._verse_watcher = None
    observer_feed.begin({'streams': {
        'primary': {'language': 'en', 'provider': 'deepgram', 'enabled': True},
        'secondary': {'language': 'ml', 'provider': 'sarvam', 'enabled': True}},
        'bible_translation': 'KJV'}, origin='callback-replay')
    observer_feed.emit('state', state='callback_replay')
    primary = engine.create_transcript_handler(case.ctrl, False, '[PRI-TEST]', engine.parse_eng)
    secondary = engine.create_sarvam_transcript_handler(case.ctrl, True, '[SEC-TEST]', engine.parse_ml)
    primary('John 3:16', True)
    with patch.object(engine, 'translate_to_english', return_value='John 3:16'):
        secondary('യോഹന്നാൻ 3:16', True)
    accepted = case.events('COMMAND_ACCEPTED')[-1]
    observer_feed._publisher.flush()
    print(json.dumps({'ready': True, 'pid': os.getpid(), 'accepted_id': accepted['candidate_id']}), flush=True)
    for command in sys.stdin:
        if command.strip() == 'advance':
            with patch.object(engine.time, 'time', return_value=1008.0):
                primary('John 3:17', True)
                engine.CONFIRM_CALLBACK = confirmation
                case.ctrl.send_verse('John 3:18', confidence=.2, source='REPLAY', stream='secondary')
            observer_feed._publisher.flush()
            print(json.dumps({'advanced': True}), flush=True)
        elif command.strip() == 'finish':
            break
finally:
    release_confirmation.set()
    confirmation_done.wait(.2)
    case.tearDown()
    case.doCleanups()
    observer_feed._publisher.close()
