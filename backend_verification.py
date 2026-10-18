"""Explicit frozen-backend QA adapter. Never selected for normal recognition."""
import asyncio
import datetime as dt
import time
import json
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
            translated = 'John 3:16'
            if engine._verse_watcher is not None or engine.LIVE_POINTS_ENABLED:
                translated += ' The preacher is reflecting on a passage about grace and faith in this synthetic service.'
            with patch.object(engine, 'translate_to_english', return_value=translated):
                handler('യോഹന്നാൻ 3:16', True)
        else:
            handler = engine.create_transcript_handler(controller, False, '[QA-EN]', engine.parse_eng)
            handler('John 3:16', True)
            if engine._verse_watcher is not None or engine.LIVE_POINTS_ENABLED:
                handler('The preacher is reflecting on a passage about grace and faith in this synthetic service. '
                        'These are synthetic spoken notes used only to exercise the existing outline and watcher processing with no live microphone.', True)
            await asyncio.sleep(4)
            handler('John 3:17', True)
            controller.send_verse('John 3:18', confidence=.2, source='BACKEND-VERIFICATION', stream='secondary')
            if engine.LIVE_POINTS_ENABLED:
                handler('The next synthetic section adds enough new spoken material to exercise another outline update while an operator corrects the notes.', True)
        await engine.stop_event.wait()
    with ExitStack() as stack:
        if engine.LIVE_POINTS_ENABLED:
            real_outline_loop=engine.live_points_loop
            # Only explicit QA accelerates the outline interval/cooldown. Its
            # transcript/model transport is fake; delivery guards stay intact.
            stack.enter_context(patch.object(engine,'live_points_loop',lambda:real_outline_loop(interval=.5)))
            stack.enter_context(patch.object(engine,'_LIVE_OUTLINE_COOLDOWN',.1))
            stack.enter_context(patch.object(engine,'_live_outline_last_dispatch',0))
        # Explicit QA only: exercise the real warmup loop with synthetic client
        # completions. Slow calls prove recognition/Stop remain responsive;
        # the deliberately private failure must never enter dashboard status.
        def warm_completion(role, **_kwargs):
            if role=='outline' and _kwargs.get('messages',[{}])[0].get('content')!='Reply with the single word: OK':
                time.sleep(3)
                return engine._GroqResponse('SYNTHETIC SERMON OUTLINE\n• Grace and faith in the synthetic service.\n• Notes come only from the synthetic spoken material.')
            if role == 'watcher' and _kwargs.get('messages', [{}])[0].get('role') == 'system':
                system = _kwargs['messages'][0]['content']
                reference = 'John 3:20' if 'Malayalam' in system else 'John 3:19'
                return engine._GroqResponse(json.dumps(dict(is_reference=True,confidence=.7,
                    suggested_reference=reference,reasoning='Synthetic paraphrase for isolated watcher verification.',
                    explicit_or_implied='implied')))
            time.sleep(4)
            if role == 'summary':
                raise engine.LocalLLMError('auth', 'SECRET-QA-ENDPOINT-KEY')
            return engine._GroqResponse('OK')
        for role, client in engine.local_llm_clients.items():
            stack.enter_context(patch.object(client.chat.completions, 'create',
                side_effect=lambda _role=role, **kwargs: warm_completion(_role, **kwargs)))
        for name, value in [('VerseController', lambda: controller), ('reconcile_chromedriver_cache', Mock()),
                            ('multi_fetch', Mock(return_value='Isolated verse text')), ('_trigger_atem_keyer', Mock()),
                            ('send_to_discord', Mock()), ('_start_bot_bridge', None),
                            ('PANIC_KEY', None),
                            ('launch_stt_task', lambda _ctrl, is_secondary=False: asyncio.create_task(speech(is_secondary)))]:
            stack.enter_context(patch.object(engine, name, value))
        stack.enter_context(patch('requests.sessions.Session.request', side_effect=AssertionError('Live HTTP forbidden in verification')))
        yield
