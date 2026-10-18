"""Explicit frozen-backend QA adapter. Never selected for normal recognition."""
import asyncio
import datetime as dt
from contextlib import contextmanager, ExitStack
from unittest.mock import Mock, patch


def verification_time():
    """Fixed Sunday Malayalam service; selected only by the explicit QA host."""
    return dt.datetime(2026, 10, 18, 12)


@contextmanager
def isolated_engine(engine):
    controller = engine.VerseController()
    controller.driver = Mock()
    controller.driver.switch_to = Mock()
    type(controller.driver.switch_to).alert = property(lambda _: (_ for _ in ()).throw(RuntimeError('No alert')))
    controller.box, controller.btn = object(), object()
    controller.vv_version = 'verseview11'
    controller.connect = Mock(return_value=True)
    async def speech(secondary):
        if secondary:
            await asyncio.sleep(.2)
            handler = engine.create_sarvam_transcript_handler(controller, True, '[QA-ML]', engine.parse_ml)
            with patch.object(engine, 'translate_to_english', return_value='John 3:16'):
                handler('യോഹന്നാൻ 3:16', True)
        else:
            handler = engine.create_transcript_handler(controller, False, '[QA-EN]', engine.parse_eng)
            handler('John 3:16', True)
            await asyncio.sleep(4)
            handler('John 3:17', True)
            controller.send_verse('John 3:18', confidence=.2, source='BACKEND-VERIFICATION', stream='secondary')
        await engine.stop_event.wait()
    with ExitStack() as stack:
        for name, value in [('VerseController', lambda: controller), ('reconcile_chromedriver_cache', Mock()),
                            ('multi_fetch', Mock(return_value='Isolated verse text')), ('_trigger_atem_keyer', Mock()),
                            ('send_to_discord', Mock()), ('_start_bot_bridge', None),
                            ('launch_stt_task', lambda _ctrl, is_secondary=False: asyncio.create_task(speech(is_secondary)))]:
            stack.enter_context(patch.object(engine, name, value))
        stack.enter_context(patch('requests.sessions.Session.request', side_effect=AssertionError('Live HTTP forbidden in verification')))
        yield
