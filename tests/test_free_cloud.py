"""Free routing regression checks. All provider traffic is fake."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import sqlite3

import requests
from free_cloud import CloudError, FreeCloudRouter, GROQ_MODEL, Limits, UsageLedger, input_bound
from contextual_watcher import ContextualVerseWatcher, WatcherConfig


class FreeCloudTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = 100000
        self.clock = lambda: self.now
        self.ledger = UsageLedger(Path(self.tmp.name) / 'usage.db', self.clock)
        self.post = Mock(return_value=self.reply())
        self.config = {'verified_free_providers': ['groq', 'gemini', 'cloudflare']}
        self.creds = {'groq': 'TEST-ONLY', 'gemini': 'TEST-ONLY', 'cloudflare': 'TEST-ONLY',
                      'cloudflare_account_id': 'a' * 32}
        self.router = FreeCloudRouter(self.config, self.creds, self.ledger, self.post, self.clock)
        self.messages = [{'role': 'user', 'content': 'ordinary public test text'}]

    @staticmethod
    def reply(content='NONE', code=200, usage=True):
        result = Mock(status_code=code, headers={}, text='provider secret TEST-ONLY')
        result.json.return_value = {'choices': [{'message': {'content': content}, 'finish_reason': 'stop'}]}
        if usage:
            result.json.return_value['usage'] = {'prompt_tokens': 100, 'completion_tokens': 5}
        return result

    def rows(self):
        with closing(sqlite3.connect(self.ledger.path)) as db:
            return db.execute('SELECT role,inp,out,neurons FROM calls').fetchall()

    def test_allowlist_and_entitlement_fail_before_network(self):
        for routes in ({'verse': {'provider': 'cerebras', 'model': 'gpt-oss-120b'}},
                       {'verse': {'provider': 'groq', 'model': 'paid-or-unknown'}}):
            self.config['routes'] = routes
            with self.assertRaises(CloudError): self.router.complete('verse', self.messages)
        self.config.pop('routes')
        self.config['verified_free_providers'] = []
        with self.assertRaises(CloudError): self.router.complete('verse', self.messages)
        self.post.assert_not_called()

    def test_current_groq_mode_bound_cache_and_actual_usage(self):
        for _ in range(2): self.router.complete('verse', self.messages, max_tokens=10000)
        self.post.assert_called_once()
        request = self.post.call_args.kwargs
        self.assertEqual(request['json']['model'], GROQ_MODEL)
        self.assertEqual(request['json']['reasoning_effort'], 'none')
        self.assertEqual(request['json']['max_tokens'], 48)
        self.assertFalse(request['allow_redirects'])
        self.assertEqual(self.rows()[0][1:3], (100, 5))
        self.assertNotIn('TEST-ONLY', str(self.router.snapshot()))

    def test_shared_atomic_budget_survives_new_router_and_reserves_verse(self):
        limits = Limits(30, 1000, 8000, 200000)
        for _ in range(20):
            self.ledger.reserve('groq', GROQ_MODEL, 'translation', 1, 1, 0, limits)
        with self.assertRaises(CloudError):
            self.ledger.reserve('groq', GROQ_MODEL, 'translation', 1, 1, 0, limits)
        other = UsageLedger(self.ledger.path, self.clock)
        for _ in range(10): other.reserve('groq', GROQ_MODEL, 'verse', 1, 1, 0, limits)
        with self.assertRaises(CloudError): other.reserve('groq', GROQ_MODEL, 'verse', 1, 1, 0, limits)
        self.now += 61
        other.reserve('groq', GROQ_MODEL, 'verse', 1, 1, 0, limits)

    def test_concurrent_streams_have_one_global_watcher_slot(self):
        def attempt(_):
            try:
                self.ledger.reserve('cloudflare', 'test', 'watcher', 100, 220, 1, Limits(30, 2000, 10000, 100000))
                return True
            except CloudError: return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(attempt, range(8))), 1)

    def test_daily_neurons_shared_between_models_and_failed_reservations_kept(self):
        limits = Limits(30, 2000, 100000, 1000000)
        self.ledger.reserve('cloudflare', 'model-a', 'watcher', 100, 220, 8999, limits)
        self.now += 11
        with self.assertRaises(CloudError):
            self.ledger.reserve('cloudflare', 'model-b', 'watcher', 100, 220, 2, limits)
        self.assertEqual(len(self.rows()), 1)

    def test_rate_quota_auth_model_transport_and_truncation_have_no_retry(self):
        for status, kind in [(401,'auth'), (403,'permission'), (402,'quota'), (404,'model'), (429,'rate'), (503,'transport')]:
            with self.subTest(status=status):
                self.post.return_value = self.reply(code=status)
                # Separate model holds from previous subcases; advance beyond their expiry.
                self.now += 86401
                with self.assertRaises(CloudError) as caught:
                    self.router.complete('verse', self.messages)
                self.assertEqual(caught.exception.kind, kind)
                self.assertNotIn('TEST-ONLY', str(caught.exception))
        self.assertEqual(self.post.call_count, 6)
        self.now += 86401
        self.post.side_effect = requests.ConnectionError('TEST-ONLY credential in exception')
        with self.assertRaises(CloudError) as caught: self.router.complete('verse', self.messages)
        self.assertEqual(caught.exception.kind, 'transport')
        self.assertNotIn('TEST-ONLY', str(caught.exception))
        self.post.side_effect = None
        truncated = self.reply()
        truncated.json.return_value['choices'][0]['finish_reason'] = 'length'
        self.post.return_value = truncated
        with self.assertRaises(CloudError) as caught: self.router.complete('verse', self.messages)
        self.assertEqual(caught.exception.kind, 'incomplete')

    def test_provider_hold_prevents_subsequent_dispatch(self):
        self.post.return_value = self.reply(code=429)
        for _ in range(2):
            with self.assertRaises(CloudError): self.router.complete('verse', self.messages)
        self.post.assert_called_once()

    def test_server_remaining_headers_preserve_verse_reserve(self):
        self.ledger.observe_groq({'x-ratelimit-remaining-requests':'199',
                                  'x-ratelimit-remaining-tokens':'4000'})
        limit = Limits(30,1000,8000,200000)
        with self.assertRaises(CloudError):
            self.ledger.reserve('groq',GROQ_MODEL,'translation',100,48,0,limit)
        self.ledger.reserve('groq',GROQ_MODEL,'verse',100,48,0,limit)

    def test_language_routing_is_explicit_and_keeps_shared_watcher_budget(self):
        en = self.router.route('watcher','en')
        ml = self.router.route('watcher','ml')
        self.assertEqual(en,('cloudflare','@cf/qwen/qwen3-30b-a3b-fp8'))
        self.assertEqual(ml,('groq',GROQ_MODEL))
        self.ledger.reserve(*en,'watcher',100,50,1,Limits(30,2000,10000,100000))
        with self.assertRaises(CloudError):
            self.ledger.reserve(*ml,'watcher',100,50,0,Limits(30,1000,8000,200000))

    def test_parallel_identical_summaries_make_one_inference(self):
        # A role lock spans cache lookup through completion; independent streams
        # cannot both pay for an identical in-flight request.
        self.config['routes'] = {'summary': {'provider':'groq','model':GROQ_MODEL}}
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _:self.router.complete('summary', self.messages,
                                                                  max_tokens=100),range(4)))
        self.post.assert_called_once()
        self.assertEqual(len(results),4)

    def test_busy_watcher_skips_instead_of_queueing_after_a_timeout(self):
        lock = self.router.role_locks['watcher']
        lock.acquire()
        try:
            with self.assertRaises(CloudError) as caught:
                self.router.complete('watcher',self.messages)
            self.assertEqual(caught.exception.kind,'busy')
            self.post.assert_not_called()
        finally: lock.release()

    def test_malayalam_bound_and_long_input_rejection_do_not_truncate(self):
        self.assertGreater(input_bound([{'role': 'user', 'content': 'ദൈവം സ്നേഹമാണ്'}]),
                           input_bound([{'role': 'user', 'content': 'God is love'}]))
        long = [{'role': 'user', 'content': 'A' * 20000}]
        with self.assertRaises(CloudError) as caught: self.router.complete('verse', long)
        self.assertEqual(caught.exception.kind, 'context')
        self.post.assert_not_called()
        self.assertEqual(len(long[0]['content']), 20000)

    def test_gemini_summary_count_finish_thought_usage_and_stable_cache(self):
        counted = Mock(status_code=200)
        counted.json.return_value = {'totalTokens': 100}
        generated = Mock(status_code=200)
        generated.json.return_value = {'candidates': [{'finishReason':'STOP',
            'content': {'parts':[{'text':'private thought', 'thought':True}, {'text':'Public notes'}]}}],
            'usageMetadata': {'promptTokenCount':100,'candidatesTokenCount':20,'thoughtsTokenCount':30}}
        self.post.side_effect = [counted, generated]
        result = self.router.complete('summary', self.messages, cache_key=['stable transcript'])
        again = self.router.complete('summary', [{'role':'user','content':'new timestamp'}], cache_key=['stable transcript'])
        self.assertEqual(result.choices[0].message.content, 'Public notes')
        self.assertTrue(again.usage['cached'])
        self.assertEqual(self.post.call_count, 2)
        self.assertTrue(self.post.call_args_list[0].args[0].endswith(':countTokens'))
        self.assertNotIn('tools', self.post.call_args.kwargs['json'])
        self.assertEqual(self.rows()[0][1:3], (100,50))

    def test_missing_usage_retains_conservative_reservation(self):
        self.post.return_value = self.reply(usage=False)
        self.router.complete('verse', self.messages)
        self.assertEqual(self.rows()[0][1:3], (input_bound(self.messages),48))

    def test_timer_and_volume_share_floor_and_secondary_gets_a_turn(self):
        config = WatcherConfig(enabled=True, global_dispatch_gap_sec=10)
        watcher = ContextualVerseWatcher(primary_language='en', secondary_language='ml',
                                         config=config, clock=self.clock)
        text = 'Public ordinary speech that has enough words for the watcher to inspect. '
        watcher.feed(text * 3)
        watcher.feed(text * 3, is_secondary=True)
        due = watcher._collect_due_streams()
        self.assertEqual([r for r,_ in due], ['primary'])
        watcher._clear_in_flight('primary')
        self.now += 3
        watcher.feed(text * 3)
        self.assertEqual(watcher._collect_due_streams(), [])
        self.now += 7
        self.assertEqual([r for r,_ in watcher._collect_due_streams()], ['secondary'])

    def test_gemini_actual_token_count_can_admit_large_utf8_input(self):
        counted = Mock(status_code=200)
        counted.json.return_value = {'totalTokens':50000}
        generated = Mock(status_code=200)
        generated.json.return_value = {'candidates':[{'finishReason':'STOP',
            'content':{'parts':[{'text':'Complete notes'}]}}]}
        self.post.side_effect = [counted, generated]
        messages = [{'role':'user','content':'സത്യം ' * 20000}]
        self.assertGreater(input_bound(messages),250000)
        result = self.router.complete('summary',messages)
        self.assertEqual(result.choices[0].message.content,'Complete notes')
        self.assertEqual(self.post.call_args.kwargs['json']['contents'][0]['parts'][0]['text'],messages[0]['content'])

    def test_engine_free_routing_bypasses_legacy_cloud_and_local_clients(self):
        import logging
        import threading
        with patch('logging.FileHandler',return_value=logging.NullHandler()), patch.object(threading.Thread,'start'):
            import vv_streaming_master as engine
        fake = Mock()
        fake.complete.return_value = self.reply().json.return_value
        with ExitStack() as stack:
            stack.enter_context(patch.object(engine,'_free_cloud_router',self.router))
            legacy = Mock(side_effect=AssertionError('Legacy network forbidden'))
            stack.enter_context(patch.object(engine,'_local_llm_active_for',legacy))
            stack.enter_context(patch.object(engine,'cerebras_client',Mock()))
            stack.enter_context(patch.object(engine,'groq_client',None))
            self.assertTrue(engine._role_has_llm('verse'))
            engine._role_completion('verse',self.messages,None,'obsolete-model')
            primary, model, fallback, _ = engine._watcher_clients_for_provider('cerebras')
            self.assertIsNone(fallback)
            self.assertEqual(model,'free-profile')
            self.assertFalse(engine._llm_semantic_match('verse public text','unrelated speech'))
            legacy.assert_not_called()

    def test_desktop_configuration_preserves_opt_in_and_private_fields(self):
        import settings
        from desktop_backend import configuration
        from types import SimpleNamespace
        def configure(free_cloud_enabled=False,free_cloud_config=None,cloudflare_api_token='',**kw): pass
        values = {**settings.DEFAULTS,'free_cloud_enabled':True,
            'free_cloud_config':self.config,'cloudflare_api_token':'TEST-ONLY'}
        mapped = configuration(values, settings, SimpleNamespace(configure=configure),None)
        self.assertTrue(mapped['free_cloud_enabled'])
        self.assertEqual(mapped['free_cloud_config'],self.config)
        self.assertEqual(mapped['cloudflare_api_token'],'TEST-ONLY')


if __name__ == '__main__': unittest.main()
