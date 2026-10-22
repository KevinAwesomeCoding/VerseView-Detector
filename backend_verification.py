"""Explicit frozen-backend QA adapter. Never selected for normal recognition."""
import asyncio
import datetime as dt
import time
import json
from contextlib import contextmanager, ExitStack
from unittest.mock import Mock, patch


def verification_download(url,cancelled):
    """Every standalone QA sync uses this fake transport, never a real URL."""
    from urllib.parse import urlsplit
    path=urlsplit(url).path
    time.sleep(3 if path.endswith('/slow') else 1)
    if cancelled():raise ValueError('Synthetic sync cancelled')
    if path.endswith('/failure'):raise ValueError('SECRET-SYNTHETIC-SYNC-ERROR')
    if path.endswith('/invalid'):return []
    account=dict(type='service_account',project_id='SECRET-SYNTHETIC-PROJECT',private_key='SECRET-SYNTHETIC-KEY',client_email='synthetic@example.invalid')
    if path.endswith('/credential'):return account
    return dict(deepgram_api_key='SECRET-SYNCED-STT',discord_bot_token='SECRET-SYNCED-BOT',
                gcp_credentials_payload=__import__('base64').b64encode(json.dumps(account).encode()).decode(),
                language='Hindi',remote_url='https://unsupported.invalid/should-not-apply',dedup_window=0,future='unsupported')


def verification_chapter(book, chapter, translation):
    """Plain fixture text only. Frozen QA must never fetch a live Bible service."""
    return [{'num': n, 'text': f'QA fixture {translation.upper()} {book} {chapter}:{n}. Synthetic preview text; no live Bible lookup.'}
            for n in range(1, 37)]


def verification_time():
    """Fixed Sunday Malayalam service; selected only by the explicit QA host."""
    return dt.datetime(2026, 10, 18, 12)


@contextmanager
def isolated_engine(engine, silent=False, notes_fixture=False):
    controller = engine.VerseController()
    controller.driver = Mock()
    controller.driver.switch_to = Mock()
    type(controller.driver.switch_to).alert = property(lambda _: (_ for _ in ()).throw(RuntimeError('No alert')))
    controller.box, controller.btn = object(), object()
    controller.vv_version = 'verseview11'
    controller.connect = Mock(return_value=True)
    async def speech(secondary):
        if silent:
            await engine.stop_event.wait()
            return
        if secondary:
            await asyncio.sleep(.2)
            handler = engine.create_sarvam_transcript_handler(controller, True, '[QA-ML]', engine.parse_ml)
            translated = 'John 3:16'
            if engine._verse_watcher is not None or engine.LIVE_POINTS_ENABLED or notes_fixture:
                translated += ' The preacher is reflecting on a passage about grace and faith in this synthetic service.'
            with patch.object(engine, 'translate_to_english', return_value=translated):
                if engine.MALAYALAM_TRANSLITERATION:
                    handler('John 3:16 daivathinte sneham', True, {'mode':'translit'})
                else:
                    handler('യോഹന്നാൻ 3:16' + ((' ദൈവത്തിന്റെ സ്നേഹത്തെക്കുറിച്ചുള്ള സന്ദേശം.' * 100) if notes_fixture else ''), True)
        else:
            handler = engine.create_transcript_handler(controller, False, '[QA-EN]', engine.parse_eng)
            handler('John 3:16', True)
            if engine._verse_watcher is not None or engine.LIVE_POINTS_ENABLED or notes_fixture:
                handler('The preacher is reflecting on a passage about grace and faith in this synthetic service. '
                        'These are synthetic spoken notes used only to exercise the existing outline and watcher processing with no live microphone.' + ((' ORIGINAL QA sermon speech about grace and faith.' * 100) if notes_fixture else ''), True)
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
                return engine._GroqResponse(json.dumps(dict(is_reference=True,confidence=.7 if 'Malayalam' in system else .95,
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


def verification_summary(engine, snapshot, fail=False):
    """Fake only the completion transport; exercise the real summary prompt."""
    time.sleep(2)
    if fail: raise ValueError('SECRET-SYNTHETIC-SUMMARY-FAILURE')
    reply = ('SYNTHETIC SERMON NOTES\nGrace and faith from the captured sermon.\nമലയാളം — preserved fixture text.\n'
             + ''.join(f'Point {n}: Grace and faith. മലയാളം — synthetic notes for scrolling.\n' for n in range(1,181))
             + 'END OF SYNTHETIC NOTES')
    client = Mock()
    client.chat.completions.create.return_value = engine._GroqResponse(reply)
    with patch.object(engine, 'LLM_ENABLED', True), patch.object(engine, '_free_cloud_router', None), \
         patch.object(engine, '_local_llm_active_for', return_value=False), patch.object(engine, 'mistral_client', client), \
         patch('requests.sessions.Session.request', side_effect=AssertionError('Live HTTP forbidden in notes QA')):
        return engine.generate_sermon_summary(snapshot, notify=False, strict=True)
