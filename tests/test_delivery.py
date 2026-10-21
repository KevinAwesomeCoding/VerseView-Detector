"""Delivery regression tests: real engine, fake browser/LLM, no live services."""
import logging
import threading
import unittest
from unittest.mock import Mock, patch

# Keep import-time logging and the Discord maintenance thread isolated.
with patch('logging.FileHandler', return_value=logging.NullHandler()), patch.object(threading.Thread, 'start'):
    import vv_streaming_master as engine
engine.logger.disabled = True
REAL_CONNECT = engine.VerseController.connect


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patch('requests.sessions.Session.request', side_effect=AssertionError('Live HTTP forbidden')),
            patch.object(engine.VerseController, 'connect', side_effect=AssertionError('Live browser forbidden')),
            patch.object(engine, '_trigger_atem_keyer'),
            patch.object(engine, 'send_to_discord'),
            patch.object(engine, 'multi_fetch', return_value='Isolated verse text'),
            patch.object(engine, '_excerpt_since_last_advance', return_value='Isolated spoken excerpt'),
            patch.object(engine, '_mark_advance_offset'),
            patch.object(engine, '_llm_semantic_match', return_value=True),
            patch.object(engine.time, 'time', return_value=1000.0),
            patch.object(engine.time, 'sleep'),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        engine.REQUIRE_VERIFY = False
        engine.REQUIRE_MANUAL_CONFIRM = True
        engine.CONFIRM_CALLBACK = None
        engine.CONFIRM_REQUEST_CALLBACK = None
        engine.CONFIDENCE_THRESHOLD = .75
        engine.WORSHIP_MODE = False
        engine.DELIVERY_HOLD = False
        engine.VERSE_INTERRUPT_ENABLED = False
        engine.SCRIPTURE_READ_MODE = False
        engine.COOLDOWN = 3
        engine.DEDUP_WINDOW = 60
        engine.groq_client = object()
        engine.cerebras_client = None
        engine.LOCAL_LLM_ENABLED = False
        engine._last_presented_book_chapter = None
        engine._last_presented_time = 0
        engine._session_verse_high_water.clear()
        engine._verse_history.clear()
        engine.verses_cited.clear()
        engine.current_book = engine.current_chapter = engine.current_verse = None
        engine._sermon_anchor_book = engine._sermon_anchor_chapter = engine._sermon_anchor_verse = None
        engine._manual_context_set_time = 0
        engine._shutdown_flag.clear()
        engine._queue_semantic_in_flight = engine._vtc_semantic_in_flight = False
        engine._queue_last_check_time = engine._vtc_last_check_time = 0
        engine._queue_last_excerpt = engine._vtc_last_excerpt = ''
        with engine.verse_queue_lock:
            engine._clear_verse_queue('Test reset')
        engine._cancel_vtc()
        engine._delivery_events.clear()
        self.ctrl = self.controller()

    def tearDown(self):
        self.join_workers()
        engine._cancel_vtc()

    def controller(self):
        ctrl = engine.VerseController()
        ctrl.driver = Mock()
        ctrl.driver.switch_to = Mock()
        type(ctrl.driver.switch_to).alert = property(lambda _: (_ for _ in ()).throw(RuntimeError('No alert')))
        ctrl.box, ctrl.btn = object(), object()
        ctrl.vv_version = 'verseview11'
        return ctrl

    def join_workers(self):
        for worker in list(engine._active_bg_threads):
            worker.join(timeout=2)
            self.assertFalse(worker.is_alive(), 'Worker failed to finish')
        engine._active_bg_threads.clear()

    def test_operator_mode_cancels_queues_and_worship_keeps_detection_without_presentation(self):
        self.queue()
        engine.set_delivery_mode(worship=True)
        self.assertEqual(list(engine.verse_queue), [])
        engine.VERSE_INTERRUPT_ENABLED = True
        self.assertFalse(self.send())
        self.assertTrue(self.events('DETECTED'))
        self.assertTrue(any(e['stage'] == 'worship' for e in self.events('SUPPRESSED')))
        self.assertIsNone(engine._vtc_pending_ref)
        self.ctrl.driver.execute_script.assert_not_called()
        engine.set_delivery_mode(worship=False)
        self.assertEqual(list(engine.verse_queue), [])

    def test_old_approval_cannot_replay_after_worship_is_switched_on_then_off(self):
        finished = threading.Event()
        def approve(*args):
            engine.set_delivery_mode(worship=True)
            engine.set_delivery_mode(worship=False)
            finished.set()
            return True
        engine.CONFIRM_REQUEST_CALLBACK = approve
        self.assertFalse(self.ctrl.send_verse('John 3:18', confidence=.2))
        self.assertTrue(finished.wait(2))
        deadline = __import__('time').monotonic() + 2
        while self.ctrl._confirm_pending and __import__('time').monotonic() < deadline:
            threading.Event().wait(.005)
        self.ctrl.driver.execute_script.assert_not_called()
        self.assertTrue(any(e['outcome'] == 'CANCELLED' for e in engine.get_delivery_events()))

    def test_emergency_hold_or_mode_change_before_click_cannot_present(self):
        engine.set_delivery_mode(worship=False, hold=True)
        self.assertFalse(self.send()); self.ctrl.driver.execute_script.assert_not_called()
        engine.set_delivery_mode(worship=False)
        self.ctrl.driver.execute_script.side_effect = lambda *args: engine.set_delivery_mode(worship=True)
        self.assertFalse(self.send())
        self.assertEqual(self.ctrl.driver.execute_script.call_count, 1)
        self.assertFalse(self.events('COMMAND_ACCEPTED'))
        self.assertTrue(self.events('CANCELLED'))
        engine.set_delivery_mode(worship=False)

    def events(self, outcome=None):
        return [e for e in engine.get_delivery_events() if outcome is None or e['outcome'] == outcome]

    def send(self, ref='John 3:16', **kwargs):
        return engine.deliver_verse(ref, self.ctrl, source='FAST-PATH', bypass_cooldown=True, **kwargs)

    def queue(self, first=16, last=17):
        real_thread = threading.Thread
        workers = []
        def make_thread(*args, **kwargs):
            worker = real_thread(*args, **kwargs)
            workers.append(worker)
            return worker
        with patch.object(engine.threading, 'Thread', side_effect=make_thread):
            engine.queue_verse_range('John', '3', first, last, self.ctrl)
        for worker in workers:
            worker.join(timeout=2)
            self.assertFalse(worker.is_alive())

    def test_accepted_candidate_reaches_browser_with_one_id(self):
        self.assertTrue(self.send())
        self.assertEqual(self.ctrl.driver.execute_script.call_count, 2)
        events = self.events()
        self.assertEqual([e['outcome'] for e in events], ['DETECTED', 'DELIVERY_REQUESTED', 'COMMAND_ACCEPTED'])
        self.assertEqual(len({e['candidate_id'] for e in events}), 1)
        self.assertFalse(self.events('PRESENTATION_CONFIRMED'))

    def test_changed_verse_in_same_chapter_passes(self):
        self.assertTrue(self.send())
        with patch.object(engine.time, 'time', return_value=1005):
            self.assertTrue(self.send('John 3:17'))
        self.assertEqual(self.ctrl.driver.execute_script.call_count, 4)

    def test_desktop_bot_keeps_real_worship_guard_and_candidate_acceptance(self):
        from types import SimpleNamespace
        from desktop_bot_bridge import ManagedBotBridge
        bridge=ManagedBotBridge(SimpleNamespace(engine=engine,stop_requested=threading.Event()))
        with patch.object(engine,'_controller',self.ctrl):
            engine.WORSHIP_MODE=True
            self.assertFalse(bridge.present('John 3:19','a'*32))
            self.assertTrue(any(e['candidate_id']=='a'*32 and e['stage']=='worship' and e['outcome']=='SUPPRESSED' for e in self.events()))
            self.assertFalse(self.events('COMMAND_ACCEPTED'))
            engine.WORSHIP_MODE=False
            self.assertTrue(bridge.present('John 3:20','b'*32))
            accepted=self.events('COMMAND_ACCEPTED')[-1]
            self.assertEqual((accepted['candidate_id'],accepted['source'],accepted['stream']),('b'*32,'DISCORD-MANUAL','unknown'))

    def test_desktop_watcher_manual_send_reaches_actual_delivery_and_keeps_worship_guard(self):
        from types import SimpleNamespace
        from desktop_suggestions import WatcherInbox
        inbox=WatcherInbox(engine,lambda:True)
        receive=inbox.prepare(True)
        def suggestion(ref):
            return SimpleNamespace(suggested_reference=ref,status='passive_suggest',confidence=.7,
                stream='secondary',language='ml',reasoning='Synthetic advice')
        with patch.object(engine,'_controller',self.ctrl):
            receive(suggestion('John 3:19'))
            identity=inbox.snapshot()['rows'][0]['id']
            engine.WORSHIP_MODE=True
            inbox.send(identity);inbox.join()
            row=inbox.snapshot()['rows'][0]
            self.assertEqual(row['state'],'review')
            self.assertTrue(any(e['candidate_id']==row['candidate_id'] and e['stage']=='worship' and e['outcome']=='SUPPRESSED' for e in self.events()))
            self.assertFalse(self.events('COMMAND_ACCEPTED'))
            engine.WORSHIP_MODE=False
            receive(suggestion('John 3:20'))
            identity=inbox.snapshot()['rows'][-1]['id']
            inbox.send(identity);inbox.join()
            row=inbox.snapshot()['rows'][-1]
            self.assertEqual(row['state'],'accepted')
            event=self.events('COMMAND_ACCEPTED')[-1]
            self.assertEqual((event['candidate_id'],event['source'],event['stream']),
                             (row['candidate_id'],'WATCHER-MANUAL','secondary'))

    def test_failed_connection_does_not_poison_retry(self):
        self.ctrl.driver = None
        self.ctrl.connect = Mock(return_value=False)
        self.assertFalse(self.send())
        self.assertEqual(engine._last_presented_time, 0)
        self.assertEqual(self.ctrl.history, {})
        self.ctrl.driver = Mock()
        with patch.object(engine.time, 'time', return_value=1001):
            self.assertTrue(self.send())
        self.assertEqual(self.events('DELIVERY_FAILED')[0]['reason'], 'Controller connection failed')

    def test_failed_input_update_does_not_poison_retry(self):
        self.ctrl.driver.execute_script.side_effect = RuntimeError('secret-content-must-not-be-logged')
        self.assertFalse(self.send())
        self.assertEqual(self.ctrl.history, {})
        self.assertEqual(engine._last_presented_time, 0)
        self.ctrl.driver = Mock()
        self.assertTrue(self.send())
        self.assertNotIn('secret-content', str(self.events()))

    def test_uncertain_click_does_not_blindly_retry(self):
        self.ctrl.driver.execute_script.side_effect = [None, RuntimeError('transport lost')]
        self.assertFalse(self.send())
        self.assertTrue(self.events('DELIVERY_FAILED')[-1]['delivery_uncertain'])
        self.assertEqual(self.ctrl.history, {})
        self.ctrl.driver = Mock()
        self.assertFalse(self.send())
        self.ctrl.driver.execute_script.assert_not_called()
        self.assertEqual(self.events('SUPPRESSED')[-1]['guard'], 'uncertain_command')

    def test_suppression_does_not_extend_cooldown(self):
        self.assertTrue(self.send())
        for tick in (1005, 1009, 1015, 1030, 1059):
            with patch.object(engine.time, 'time', return_value=tick):
                self.assertFalse(self.send())
        self.assertEqual(engine._last_presented_time, 1000)
        with patch.object(engine.time, 'time', return_value=1061):
            self.assertTrue(self.send())
        self.assertTrue(all('guard' in e for e in self.events('SUPPRESSED')))

    def test_global_cooldown_kept(self):
        self.assertTrue(self.send())
        self.assertFalse(engine.deliver_verse('Romans 8:1', self.ctrl, source='PARSER'))
        self.assertEqual(self.events('SUPPRESSED')[-1]['guard'], 'COOLDOWN')

    def test_worship_mode_kept(self):
        engine.WORSHIP_MODE = True
        self.assertFalse(self.send())
        self.ctrl.driver.execute_script.assert_not_called()
        self.assertEqual(self.events('SUPPRESSED')[-1]['guard'], 'WORSHIP_MODE')

    def test_invalid_candidate(self):
        self.assertFalse(self.send('John 3:999'))
        self.ctrl.driver.execute_script.assert_not_called()
        self.assertTrue(self.events('INVALID'))

    def test_chapter_only_does_not_report_delivery(self):
        self.assertFalse(self.send('John 3'))  # context update is not delivery
        self.ctrl.driver.execute_script.assert_not_called()
        self.assertFalse(self.events('COMMAND_ACCEPTED'))
        self.assertEqual(engine.current_chapter, '3')

    def test_hear_twice_verification_kept(self):
        engine.REQUIRE_VERIFY = True
        self.assertFalse(engine.deliver_verse('John 3:16', self.ctrl, source='PARSER'))
        self.assertEqual(self.events('SUPPRESSED')[-1]['guard'], 'REQUIRE_VERIFY')
        self.assertTrue(engine.deliver_verse('John 3:16', self.ctrl, source='PARSER'))

    def test_manual_confirmation_holds_and_reuses_id(self):
        entered, release = threading.Event(), threading.Event()
        def confirm(*_):
            entered.set()
            if not release.wait(2):
                raise RuntimeError('test timed out')
            return True
        engine.CONFIRM_CALLBACK = confirm
        real_thread = threading.Thread
        workers = []
        def make_thread(*args, **kwargs):
            worker = real_thread(*args, **kwargs)
            workers.append(worker)
            return worker
        with patch.object(engine.threading, 'Thread', side_effect=make_thread):
            self.assertFalse(engine.deliver_verse('John 3:16', self.ctrl, confidence=.5, source='PARSER'))
        self.assertTrue(entered.wait(1))
        self.ctrl.driver.execute_script.assert_not_called()
        self.assertFalse(engine.deliver_verse('John 3:16', self.ctrl, confidence=.5, source='PARSER'))
        release.set()
        workers[0].join(2)
        self.assertFalse(workers[0].is_alive())
        pending_id = self.events('MANUAL_CONFIRM_REQUIRED')[0]['candidate_id']
        self.assertEqual(self.events('COMMAND_ACCEPTED')[0]['candidate_id'], pending_id)
        self.assertEqual(len(workers), 1)

    def test_contextual_confirmation_retains_candidate_identity_and_guards(self):
        for worship in (False, True):
            with self.subTest(worship=worship):
                self.ctrl = self.controller()
                engine._delivery_events.clear()
                engine._last_presented_time = 0
                engine._last_presented_book_chapter = None
                engine.WORSHIP_MODE = False
                calls, workers = [], []
                real_thread = threading.Thread
                def confirm(*args):
                    calls.append(args)
                    engine.WORSHIP_MODE = worship
                    return True
                def make_thread(*args, **kwargs):
                    worker = real_thread(*args, **kwargs)
                    workers.append(worker)
                    return worker
                engine.CONFIRM_REQUEST_CALLBACK = confirm
                with patch.object(engine.threading, 'Thread', side_effect=make_thread):
                    engine.deliver_verse('John 3:18', self.ctrl, confidence=.2, source='PARSER', stream='secondary')
                workers[0].join(2)
                self.assertFalse(workers[0].is_alive())
                held_id = self.events('MANUAL_CONFIRM_REQUIRED')[0]['candidate_id']
                self.assertEqual(calls, [('John 3:18', .2, held_id, 'PARSER', 'secondary')])
                if worship:
                    self.assertFalse(self.events('COMMAND_ACCEPTED'))
                    self.assertEqual(self.events('SUPPRESSED')[-1]['guard'], 'WORSHIP_MODE')
                else:
                    self.assertEqual(self.events('COMMAND_ACCEPTED')[0]['candidate_id'], held_id)
                engine.WORSHIP_MODE = False

    def test_manual_rejection_and_callback_exception(self):
        for result in (False, RuntimeError('private callback content')):
            with self.subTest(result=type(result).__name__):
                engine.CONFIRM_CALLBACK = Mock(side_effect=result) if isinstance(result, Exception) else Mock(return_value=result)
                workers = []
                real_thread = threading.Thread
                def make_thread(*args, **kwargs):
                    worker = real_thread(*args, **kwargs)
                    workers.append(worker)
                    return worker
                with patch.object(engine.threading, 'Thread', side_effect=make_thread):
                    engine.deliver_verse('John 3:16', self.ctrl, confidence=.5, source='PARSER')
                workers[0].join(2)
                self.assertFalse(workers[0].is_alive())
                self.assertEqual(self.ctrl._confirm_pending, set())
        self.assertTrue(self.events('CANCELLED'))
        self.assertTrue(self.events('ERROR'))
        self.ctrl.driver.execute_script.assert_not_called()

    def test_queued_verse_releases_with_original_id_and_stream(self):
        token = engine.STT_STREAM_ROLE.set('secondary')
        try:
            self.queue()
        finally:
            engine.STT_STREAM_ROLE.reset(token)
        candidate_id = engine.verse_queue[0][3]
        engine.check_verse_queue('ignored', self.ctrl)
        self.join_workers()
        self.assertEqual(engine.verse_queue, [])
        accepted = self.events('COMMAND_ACCEPTED')[0]
        self.assertEqual(accepted['candidate_id'], candidate_id)
        self.assertEqual(accepted['stream'], 'secondary')
        self.assertEqual(accepted['reference'], 'John 3:17')

    def test_queue_replacement_and_expiry_are_explained(self):
        self.queue()
        first_id = engine.verse_queue[0][3]
        self.queue(first=17, last=18)
        self.assertTrue(any(e['candidate_id'] == first_id for e in self.events('CANCELLED')))
        with patch.object(engine.time, 'time', return_value=1181):
            engine.check_verse_queue('ignored', self.ctrl)
        self.assertEqual(engine.verse_queue, [])
        self.assertTrue(self.events('EXPIRED'))

    def test_replaced_range_fetch_cannot_repopulate_queue(self):
        entered, release = threading.Event(), threading.Event()
        def fetch(ref):
            if ref == 'John 3:17':
                entered.set()
                if not release.wait(2):
                    raise RuntimeError('test timed out')
            return 'Isolated verse'
        real_thread = threading.Thread
        workers = []
        def make_thread(*args, **kwargs):
            worker = real_thread(*args, **kwargs)
            workers.append(worker)
            return worker
        with patch.object(engine, 'fetch_verse_text', side_effect=fetch), patch.object(engine.threading, 'Thread', side_effect=make_thread):
            engine.queue_verse_range('John', '3', 16, 17, self.ctrl)
            self.assertTrue(entered.wait(1))
            engine.queue_verse_range('John', '3', 17, 18, self.ctrl)
            release.set()
            for worker in workers:
                worker.join(2)
                self.assertFalse(worker.is_alive())
        self.assertEqual([entry[0] for entry in engine.verse_queue], ['John 3:18'])
        self.assertEqual(len(self.events('CANCELLED')), 1)

    def test_queue_fetch_and_send_failures_are_recorded(self):
        with patch.object(engine, 'fetch_verse_text', return_value=None):
            self.queue()
        self.assertEqual(engine.verse_queue, [])
        self.assertEqual(self.events('DELIVERY_FAILED')[-1]['stage'], 'fetch')
        self.queue()
        self.ctrl.driver.execute_script.side_effect = RuntimeError('send failed')
        engine.check_verse_queue('ignored', self.ctrl)
        self.join_workers()
        self.assertEqual(engine.verse_queue, [])
        self.assertEqual(self.events('DELIVERY_FAILED')[-1]['stage'], 'browser_command')

    def test_queue_semantic_exception_remains_visible(self):
        self.queue()
        with patch.object(engine, '_llm_semantic_match', side_effect=RuntimeError('private excerpt')):
            engine.check_verse_queue('ignored', self.ctrl)
            self.join_workers()
        self.assertTrue(self.events('ERROR'))
        self.assertEqual(len(engine.verse_queue), 1)  # pending, can be checked again
        self.assertFalse(engine._queue_semantic_in_flight)

    def test_queue_book_change_cancels(self):
        self.queue()
        engine.current_book, engine.current_chapter = 'Romans', '8'
        engine.check_verse_queue('ignored', self.ctrl)
        self.assertEqual(engine.verse_queue, [])
        self.assertTrue(self.events('CANCELLED'))

    def test_missing_controller_and_controls(self):
        self.assertFalse(engine.deliver_verse('John 3:16', None))
        self.ctrl.btn = None
        self.assertFalse(self.send())
        self.assertEqual(len(self.events('DELIVERY_FAILED')), 2)

    def test_concurrent_candidates_produce_one_command(self):
        barrier = threading.Barrier(8)
        def send():
            barrier.wait()
            self.send()
        workers = [threading.Thread(target=send) for _ in range(8)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(2)
            self.assertFalse(worker.is_alive())
        self.assertEqual(self.ctrl.driver.execute_script.call_count, 2)
        self.assertEqual(len(self.events('COMMAND_ACCEPTED')), 1)

    def test_post_command_error_preserves_accepted_state(self):
        with patch.object(engine, '_trigger_atem_keyer', side_effect=RuntimeError('ancillary failure')):
            self.assertTrue(self.send())
        self.assertTrue(self.events('COMMAND_ACCEPTED'))
        self.assertEqual(self.events('ERROR')[-1]['stage'], 'post_command')
        self.ctrl.driver = Mock()
        self.assertFalse(self.send())
        self.ctrl.driver.execute_script.assert_not_called()

    def test_vtc_replacement_expiry_and_release(self):
        engine.VERSE_INTERRUPT_ENABLED = True
        self.assertFalse(self.send())
        first_id = engine._vtc_candidate_id
        self.assertFalse(self.send('John 3:17'))
        self.assertTrue(any(e['candidate_id'] == first_id for e in self.events('CANCELLED')))
        candidate_id = engine._vtc_candidate_id
        engine.check_vtc('ignored', self.ctrl)
        self.join_workers()
        self.assertEqual(self.events('COMMAND_ACCEPTED')[-1]['candidate_id'], candidate_id)
        self.assertIsNone(engine._vtc_pending_ref)
        self.send('John 3:18')
        engine._vtc_expire('John 3:18', engine._vtc_candidate_id)
        self.assertTrue(self.events('EXPIRED'))

    def test_vtc_fetch_failure_preserves_existing_fallback(self):
        engine.VERSE_INTERRUPT_ENABLED = True
        with patch.object(engine, 'fetch_verse_text', return_value=None):
            self.assertTrue(self.send())
        self.assertTrue(self.events('ERROR'))
        self.assertTrue(self.events('COMMAND_ACCEPTED'))

    def test_local_only_queue_and_vtc_can_match(self):
        engine.groq_client = engine.cerebras_client = None
        with patch.object(engine, '_local_llm_active_for', return_value=True):
            self.queue()
            engine.check_verse_queue('ignored', self.ctrl)
            self.join_workers()
            self.assertTrue(self.events('COMMAND_ACCEPTED'))
            engine.VERSE_INTERRUPT_ENABLED = True
            self.send('John 3:18')
            engine.check_vtc('ignored', self.ctrl)
            self.join_workers()
            self.assertEqual(self.events('COMMAND_ACCEPTED')[-1]['reference'], 'John 3:18')

    def test_delivery_diagnostics_are_bounded_and_copied(self):
        for index in range(350):
            engine._delivery_event(str(index), 'John 3:16', 'PARSER', 'primary', 'test', 'SUPPRESSED', 'Test')
        snapshot = engine.get_delivery_events()
        self.assertEqual(len(snapshot), 300)
        snapshot[0]['reason'] = 'tampered'
        self.assertEqual(engine.get_delivery_events()[0]['reason'], 'Test')

    def test_normalized_references_share_dedup_state(self):
        self.assertTrue(self.send(' john 03:016 '))
        self.assertFalse(self.send('John 3:16'))
        self.assertEqual(len(self.events('COMMAND_ACCEPTED')), 1)

    def test_scripture_progression_only_after_command_acceptance(self):
        engine.SCRIPTURE_READ_MODE = True
        engine._sr_locked_book, engine._sr_locked_chapter = 'John', '3'
        engine._sr_expected_verse = 16
        engine.WORSHIP_MODE = True
        self.assertFalse(self.send())
        self.assertEqual(engine._sr_expected_verse, 16)
        engine.WORSHIP_MODE = False
        self.assertTrue(self.send())
        self.assertEqual(engine._sr_expected_verse, 17)

    def test_scripture_and_quarantine_guards_are_reported(self):
        engine.SCRIPTURE_READ_MODE = True
        engine._sr_locked_book, engine._sr_locked_chapter = 'Romans', '8'
        engine._sr_expected_verse = 1
        self.assertFalse(self.send())
        self.assertEqual(self.events('SUPPRESSED')[-1]['guard'], 'SCRIPTURE_READ_MODE')
        engine.SCRIPTURE_READ_MODE = False
        with patch.object(engine, '_in_system_quarantine', return_value=True):
            self.assertFalse(engine.deliver_verse('John 3:16', self.ctrl, source='CONTEXTUAL'))
        self.assertEqual(self.events('SUPPRESSED')[-1]['guard'], 'CONTEXT_FLOOR_MANUAL_CONTEXT_BYPASS')

    def test_sdk_callback_stream_and_exception_boundary(self):
        for factory in (engine.create_transcript_handler, engine.create_sarvam_transcript_handler):
            with self.subTest(factory=factory.__name__):
                seen = []
                def process(*_, **__):
                    seen.append(engine._safe_stream_role())
                    raise RuntimeError('private transcript')
                callback = factory(self.ctrl, True, '[SEC-TEST]', engine.parse_eng)
                with patch.object(engine, '_process_transcript_blob', side_effect=process), patch.object(engine, 'translate_to_english', return_value='Isolated text'):
                    with self.assertRaises(RuntimeError):
                        callback('Isolated text', True)
                self.assertEqual(seen, ['secondary'])
                self.assertIsNone(engine._safe_stream_role())
                self.assertEqual(self.events('ERROR')[-1]['stream'], 'secondary')
                self.assertNotIn('private transcript', str(self.events()))

    def test_onwards_failure_does_not_advance(self):
        engine.onwards_active = True
        engine.onwards_target_ref = 'John 3:17'
        engine.onwards_target_text = 'Isolated words'
        engine.onwards_trigger = 'isolated words'
        engine.onwards_verse = 16
        engine._onwards_last_check_time = 0
        engine._onwards_semantic_in_flight = False
        self.ctrl.driver = None
        self.ctrl.connect = Mock(return_value=False)
        with patch.object(engine, '_reset_onwards_timer') as timer, patch.object(engine, '_fetch_next_onwards') as fetch:
            self.assertFalse(engine._check_onwards_advance('isolated words', self.ctrl))
            self.assertEqual(engine.onwards_verse, 16)
            timer.assert_not_called()
            fetch.assert_not_called()
        engine.onwards_active = False

    def test_version_and_legacy_selector_paths_with_fake_selenium(self):
        import sys
        from types import ModuleType, SimpleNamespace
        # Exercise the actual connect implementation and actual version detector.
        module_names = ('selenium', 'selenium.webdriver', 'selenium.webdriver.chrome',
                        'selenium.webdriver.chrome.service', 'selenium.webdriver.common',
                        'selenium.webdriver.common.by', 'selenium.webdriver.support',
                        'selenium.webdriver.support.ui', 'selenium.webdriver.support.expected_conditions',
                        'webdriver_manager', 'webdriver_manager.chrome')
        modules = {name: ModuleType(name) for name in module_names}
        for name, module in modules.items():
            if '.' in name:
                parent, attr = name.rsplit('.', 1)
                setattr(modules[parent], attr, module)
        modules['selenium.webdriver.chrome.service'].Service = Mock()
        modules['selenium.webdriver.common.by'].By = SimpleNamespace(ID='id', XPATH='xpath', TAG_NAME='tag')
        modules['selenium.webdriver.support.expected_conditions'].presence_of_element_located = lambda selector: selector
        modules['webdriver_manager.chrome'].ChromeDriverManager = Mock(side_effect=AssertionError('No downloads'))
        webdriver = modules['selenium.webdriver']
        webdriver.ChromeOptions = Mock()
        for version, legacy in ((10, False), (11, False), (11, True)):
            with self.subTest(version=version, legacy=legacy):
                driver = Mock()
                driver.title = f'VerseVIEW Remote {version}.0.0'
                driver.find_elements.return_value = [object()] if version == 11 else []
                input_id = 'remote_bibleRefID' if legacy else 'remotebibleRefID'
                button_id = 'remote_bible_present' if legacy else 'remotebiblepresent'
                controls = {input_id: object(), button_id: object()}
                def find(by, selector):
                    if selector not in controls:
                        raise LookupError(selector)
                    return controls[selector]
                driver.find_element.side_effect = find
                webdriver.Chrome = Mock(return_value=driver)
                wait = Mock()
                wait.until.side_effect = lambda selector: find(*selector)
                modules['selenium.webdriver.support.ui'].WebDriverWait = Mock(return_value=wait)
                with patch.dict(sys.modules, modules), patch.object(engine._glob, 'glob', return_value=['isolated-driver']), patch.object(engine.os.path, 'getmtime', return_value=0):
                    self.assertTrue(REAL_CONNECT(self.ctrl))
                self.assertEqual(self.ctrl.vv_version, f'verseview{version}')
                self.assertIs(self.ctrl.box, controls[input_id])
                self.assertIs(self.ctrl.btn, controls[button_id])
                self.ctrl.history.clear()
                self.ctrl.last_sent = None
                self.assertTrue(self.send())
                driver.execute_script.assert_any_call('arguments[0].click();', controls[button_id])


    def test_transcript_to_browser_preserves_candidate_identity(self):
        engine.PRIMARY_PARSER = engine.parse_eng
        handler = engine.create_transcript_handler(self.ctrl, True, '[SEC-TEST]', engine.parse_eng)
        handler('John 3:16', True)
        accepted = self.events('COMMAND_ACCEPTED')[-1]
        self.assertEqual(accepted['source'], 'FAST-PATH')
        self.assertEqual(accepted['stream'], 'secondary')
        self.assertEqual(len({event['candidate_id'] for event in self.events()}), 1)

    def test_observer_keeps_raw_sarvam_text_when_translation_raises(self):
        handler = engine.create_sarvam_transcript_handler(self.ctrl, True, '[SEC-TEST]', engine.parse_ml)
        with patch.object(engine, '_observer_emit') as observe, patch.object(
                engine, 'translate_to_english', side_effect=RuntimeError('translation unavailable')):
            with self.assertRaises(RuntimeError):
                handler('യോഹന്നാൻ 3:16', True)
        self.assertEqual(observe.call_args_list[0].args, ('transcript',))
        self.assertEqual(observe.call_args_list[0].kwargs['stream'], 'secondary')
        self.assertEqual(observe.call_args_list[0].kwargs['text'], 'യോഹന്നാൻ 3:16')
        self.assertEqual(self.events('ERROR')[-1]['stage'], 'transcript_callback')
        self.ctrl.driver.execute_script.assert_not_called()

    def test_false_positive_and_translation_guards_remain_explainable(self):
        engine.PRIMARY_PARSER = engine.parse_eng
        with patch.object(engine, '_is_book_as_person', return_value=True):
            self.assertFalse(engine._detect_explicit_reference('John 3:16', self.ctrl))
        self.assertEqual(self.events('SUPPRESSED')[-1]['stage'], 'parser_guard')
        engine.USE_SARVAM = True
        try:
            self.assertFalse(engine._detect_from_translation('John 3:16', self.ctrl))
            self.assertEqual(self.events('SUPPRESSED')[-1]['reason'], 'Translated text is too short')
        finally:
            engine.USE_SARVAM = False
        self.ctrl.driver.execute_script.assert_not_called()

    def test_multilingual_parser_outputs_still_deliver(self):
        for parser, text in ((engine.parse_eng, 'John 3:16'),
                             (engine.parse_hindi, 'यूहन्ना 3:16'),
                             (engine.parse_ml, 'യോഹന്നാൻ 3:16')):
            with self.subTest(parser=parser.__module__):
                refs = parser(text)
                self.assertEqual(refs, ['John 3:16'])
                ctrl = self.controller()
                self.assertTrue(engine.deliver_verse(refs[0], ctrl, bypass_cooldown=True, source='FAST-PATH'))
                self.assertEqual(ctrl.driver.execute_script.call_count, 2)

    def test_vtc_replaced_fetch_and_old_expiry_cannot_affect_new_candidate(self):
        entered, release = threading.Event(), threading.Event()
        def fetch(ref):
            if ref == 'John 3:16' and not release.is_set():
                entered.set()
                if not release.wait(2):
                    raise RuntimeError('test timed out')
            return 'Isolated verse'
        engine.VERSE_INTERRUPT_ENABLED = True
        with patch.object(engine, 'fetch_verse_text', side_effect=fetch):
            worker = threading.Thread(target=self.send)
            worker.start()
            self.assertTrue(entered.wait(1))
            first_id = engine._vtc_candidate_id
            self.send('John 3:17')
            release.set()
            worker.join(2)
            self.assertFalse(worker.is_alive())
        self.assertEqual(engine._vtc_pending_ref, 'John 3:17')
        self.send('John 3:16')
        engine._vtc_expire('John 3:16', first_id)
        self.assertEqual(engine._vtc_pending_ref, 'John 3:16')
        self.assertNotEqual(engine._vtc_candidate_id, first_id)

    def test_manual_pending_is_cancelled_when_controller_closes(self):
        entered, release = threading.Event(), threading.Event()
        def confirm(*_):
            entered.set()
            if not release.wait(2):
                raise RuntimeError('test timed out')
            return True
        engine.CONFIRM_CALLBACK = confirm
        real_thread = threading.Thread
        workers = []
        def make_thread(*args, **kwargs):
            worker = real_thread(*args, **kwargs)
            workers.append(worker)
            return worker
        with patch.object(engine.threading, 'Thread', side_effect=make_thread):
            engine.deliver_verse('John 3:16', self.ctrl, confidence=.5, source='PARSER')
        self.assertTrue(entered.wait(1))
        self.ctrl.cleanup()
        release.set()
        workers[0].join(2)
        self.assertFalse(workers[0].is_alive())
        self.assertTrue(self.events('CANCELLED'))
        self.assertFalse(self.events('COMMAND_ACCEPTED'))


    def test_hybrid_parser_acceptance_and_guard_have_correlated_events(self):
        self.assertTrue(engine.detect_verse_hybrid('John 3:16', self.ctrl, parser=engine.parse_eng))
        self.assertEqual(len({event['candidate_id'] for event in self.events()}), 1)
        self.assertTrue(self.events('COMMAND_ACCEPTED'))
        engine._delivery_events.clear()
        with patch.object(engine, '_is_book_as_person', return_value=True):
            engine.detect_verse_hybrid('John 3:17', self.ctrl, parser=engine.parse_eng)
        self.assertTrue(self.events('SUPPRESSED'))
        self.assertEqual(self.events('SUPPRESSED')[-1]['stage'], 'parser_guard')
        self.assertFalse(self.events('COMMAND_ACCEPTED'))

    def test_gui_diagnostics_refresh_is_bounded_and_read_only(self):
        # Execute the actual GUI methods with fake widgets; no Tk window or
        # import of the application (which could start its bridge) is needed.
        import ast
        from pathlib import Path
        from types import SimpleNamespace
        tree = ast.parse(Path(engine.__file__).with_name('vv_gui.py').read_text(encoding='utf-8'))
        app = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'VerseViewApp')
        method = next(node for node in app.body if isinstance(node, ast.FunctionDef) and node.name == '_update_delivery_diagnostics')
        namespace = {'engine': engine}
        exec(compile(ast.Module(body=[method], type_ignores=[]), 'vv_gui.py', 'exec'), namespace)
        for index in range(100):
            engine._delivery_event(str(index), 'John 3:16', 'PARSER', 'primary', 'test', 'SUPPRESSED', 'Test')
        box = Mock()
        box.yview.return_value = (0, 1)
        view = SimpleNamespace(_delivery_diag_snapshot=[], _delivery_diag_box=box, after=Mock())
        view._update_delivery_diagnostics = lambda: namespace['_update_delivery_diagnostics'](view)
        view._update_delivery_diagnostics()
        self.assertEqual(box.insert.call_count, 80)
        box.configure.assert_called_with(state='disabled')
        view.after.assert_called_with(500, view._update_delivery_diagnostics)
        box.reset_mock()
        view._update_delivery_diagnostics()
        box.insert.assert_not_called()

    def test_restore_keeps_both_buffers_as_metadata_without_delivery(self):
        previous = engine.get_session_snapshot()
        quarantine = (engine._manual_context_set_time, engine._quarantine_transcript_offset)
        try:
            engine.restore_session_snapshot({'transcript': 'Saved English', 'transcript_secondary': 'യോഹന്നാൻ',
                'verse_history': [{'ref': 'John 3:16', 'time': '10:00', 'layer': 'PARSER'}],
                'sermon_anchor': {'book': 'John', 'chapter': 3, 'verse': 16}})
            self.assertEqual(engine.full_sermon_transcript_secondary, 'യോഹന്നാൻ')
            self.assertEqual(engine.get_session_snapshot()['transcript_secondary'], 'യോഹന്നാൻ')
            self.assertEqual(engine.current_verse, 16)
            self.assertGreater(engine._manual_context_set_time, 0)
            self.ctrl.driver.execute_script.assert_not_called()
            engine.send_to_discord.assert_not_called()
            self.assertFalse(self.events('COMMAND_ACCEPTED'))
        finally:
            engine.restore_session_snapshot(previous)
            engine._manual_context_set_time, engine._quarantine_transcript_offset = quarantine

    def test_compact_layout_keeps_transcript_and_history_room(self):
        # Exercise Tk's geometry allocation with the actual row configuration.
        # The old weighted rows shrink the transcript below both history headers
        # when suggestions and diagnostics compete in the default window.
        import ast
        import tkinter as tk
        from pathlib import Path
        from types import SimpleNamespace
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f'Tk display unavailable: {exc}')
        self.addCleanup(root.destroy)
        root.attributes('-alpha', 0.0)
        root.geometry('750x470')
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        mid = tk.Frame(root)
        mid.grid(row=0, column=0, sticky='nsew')
        tree = ast.parse(Path(engine.__file__).with_name('vv_gui.py').read_text(encoding='utf-8'))
        statements = [node for node in ast.walk(tree)
                      if isinstance(node, ast.Expr)
                      and isinstance(node.value, ast.Call)
                      and isinstance(node.value.func, ast.Attribute)
                      and isinstance(node.value.func.value, ast.Name)
                      and node.value.func.value.id == 'mid'
                      and node.value.func.attr == 'grid_rowconfigure']
        namespace = {'mid': mid, 'self': SimpleNamespace(
            _sugg_top_weight=1000, _sugg_bottom_weight=300)}
        exec(compile(ast.Module(body=statements, type_ignores=[]),
                     'vv_gui.py', 'exec'), namespace)
        top = tk.Frame(mid, width=750, height=200)
        top.grid(row=0, column=0, sticky='nsew')
        tk.Frame(mid, height=20).grid(row=1, column=0, sticky='ew')
        tk.Frame(mid, height=300).grid(row=2, column=0, sticky='nsew')
        tk.Frame(mid, height=122).grid(row=3, column=0, sticky='ew')
        # Windows maps the native window via Configure events, not just Tk's
        # idle geometry queue. Process those events before measuring frames.
        root.update()
        root.update_idletasks()
        self.assertEqual(mid.winfo_height(), 470)
        # Two headers, manual entry and a few visible history/transcript lines.
        self.assertGreaterEqual(top.winfo_height(), 160)



if __name__ == '__main__':
    unittest.main()


class GroqCompatibilityTests(unittest.TestCase):
    def test_current_verse_model_uses_instruct_mode_with_bounded_answer(self):
        response = Mock()
        response.json.return_value = {'choices': [{'message': {'content': 'YES'}}]}
        with patch.object(engine.requests, 'post', return_value=response) as post:
            result = engine._GroqClient('FAKE-TEST-KEY').chat.completions.create(
                model=engine.GROQ_VERSE_MODEL, messages=[{'role': 'user', 'content': 'Test'}],
                temperature=0.0, max_tokens=48)
        self.assertEqual(result.choices[0].message.content, 'YES')
        body = post.call_args.kwargs['json']
        self.assertEqual(body['model'], 'qwen/qwen3.8-27b')
        self.assertEqual(body['reasoning_effort'], 'none')
        self.assertEqual(body['max_tokens'], 48)

    def test_semantic_match_routes_to_available_model_and_preserves_no_match(self):
        with patch.object(engine, 'groq_client', object()), patch.object(engine, 'cerebras_client', None), \
             patch.object(engine, 'LOCAL_LLM_ENABLED', False), \
             patch.object(engine, '_role_completion', side_effect=[engine._GroqResponse('YES'), engine._GroqResponse('NO')]) as completion:
            self.assertTrue(engine._llm_semantic_match('Verse text', 'Matching excerpt'))
            self.assertFalse(engine._llm_semantic_match('Verse text', 'Unrelated greeting'))
        for call in completion.call_args_list:
            self.assertEqual(call.kwargs['cloud_model'], engine.GROQ_VERSE_MODEL)
            self.assertEqual(call.kwargs['max_tokens'], 48)
