import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import vv_streaming_master as engine
from desktop_warmup import SessionWarmup, public_status


def client(create=None):
    return SimpleNamespace(model='SECRET-MODEL', keep_alive='30m',
                           chat=SimpleNamespace(completions=SimpleNamespace(create=create or Mock())))


def configured(clients):
    return SimpleNamespace(LOCAL_LLM_ENABLED=True, local_llm_clients=clients,
                           warm_all_local_llm_roles=engine.warm_all_local_llm_roles)


class WarmupTests(unittest.TestCase):
    def test_opt_in_and_local_roles_are_required(self):
        warmup = SessionWarmup()
        fake = configured({'verse': client()})
        for enabled, stopped, state in [(False, False, 'off'), (True, True, 'cancelled')]:
            warmup.start(fake, enabled, stopped)
            self.assertIsNone(warmup.thread)
            self.assertEqual(warmup.snapshot()['status'], state)
        fake.LOCAL_LLM_ENABLED = False
        warmup.start(fake, True)
        self.assertEqual(warmup.snapshot()['status'], 'skipped')
        fake.local_llm_clients['verse'].chat.completions.create.assert_not_called()

    def test_captured_clients_use_production_parameters_and_redact_results(self):
        clients = {role: client() for role in ('verse', 'outline', 'summary', 'watcher')}
        clients['summary'].chat.completions.create.side_effect = engine.LocalLLMError('auth', 'SECRET-ENDPOINT-KEY')
        warmup = SessionWarmup()
        warmup.start(configured(clients), True)
        warmup.thread.join(2)
        self.assertFalse(warmup.thread.is_alive())
        snapshot = warmup.snapshot()
        self.assertEqual((snapshot['status'], snapshot['total']), ('failed', 4))
        self.assertEqual(len(snapshot['roles']), 4)
        self.assertNotIn('SECRET-', str(snapshot))
        for role, value in clients.items():
            kwargs = value.chat.completions.create.call_args.kwargs
            params = engine.local_llm_role_request_params(role)
            self.assertEqual(kwargs['temperature'], params['temperature'])
            self.assertEqual(kwargs['max_tokens'], params['max_tokens'] or 16)
            self.assertEqual(kwargs.get('num_ctx'), params.get('num_ctx'))
            self.assertEqual(kwargs['model'], value.model)
        snapshot['roles'].clear()
        self.assertEqual(len(warmup.snapshot()['roles']), 4)

    def test_stop_restart_does_not_overlap_or_publish_stale_results(self):
        entered, release = threading.Event(), threading.Event()
        def blocked(**_kwargs):
            entered.set()
            if not release.wait(3): raise RuntimeError('Test release missing')
        old = configured({'outline': client(Mock(side_effect=blocked)), 'verse': client()})
        new = configured({'verse': client()})
        warmup = SessionWarmup()
        try:
            warmup.start(old, True)
            self.assertTrue(entered.wait(2))
            warmup.cancel()
            self.assertEqual(warmup.snapshot()['status'], 'cancelled')
            warmup.start(new, True)
            self.assertEqual(warmup.snapshot()['status'], 'busy')
            release.set(); warmup.thread.join(2)
            self.assertEqual(warmup.snapshot()['status'], 'busy')
            self.assertEqual(warmup.snapshot()['roles'], [])
            old.local_llm_clients['verse'].chat.completions.create.assert_not_called()
            new.local_llm_clients['verse'].chat.completions.create.assert_not_called()
            warmup.start(new, True); warmup.thread.join(2)
            self.assertEqual(warmup.snapshot()['status'], 'complete')
            new.local_llm_clients['verse'].chat.completions.create.assert_called_once()
        finally:
            release.set()
            if warmup.thread: warmup.thread.join(2)

    def test_unexpected_failure_is_private_and_status_is_allowlisted(self):
        fake = configured({'verse': client()})
        fake.warm_all_local_llm_roles = Mock(side_effect=ValueError('SECRET-UNEXPECTED'))
        warmup = SessionWarmup()
        with patch('desktop_warmup.logging.getLogger') as logger:
            warmup.start(fake, True); warmup.thread.join(2)
            logger.return_value.exception.assert_called_once()
        self.assertEqual(warmup.snapshot()['status'], 'failed')
        self.assertNotIn('SECRET-', str(warmup.snapshot()))
        projected = public_status(dict(status='failed', total=999, endpoint='SECRET', roles=[
            dict(role='verse', status='failed', elapsed_seconds=float('inf'), error='SECRET'),
            dict(role='SECRET', status='failed', elapsed_seconds=2)]))
        self.assertEqual(projected, dict(status='failed', total=4, roles=[dict(role='verse', status='failed', elapsed_seconds=0)]))
        self.assertIsNone(public_status({'status': 'SECRET'}))


if __name__ == '__main__': unittest.main()
