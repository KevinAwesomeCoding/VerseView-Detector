import copy
import inspect
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import settings
from desktop_backend import ProfileStore, BackendHost, BackendError, ProfileLock, configuration, start_problem
from observer_feed import ObserverPublisher


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)/'settings.json'
        self.path.write_text(json.dumps({**settings.DEFAULTS, 'deepgram_api_key': 'private', 'future': 42}))
        self.patcher = patch.object(settings, '_settings_path', return_value=self.path)
        self.patcher.start(); self.addCleanup(self.patcher.stop)
        directory_patch = patch.object(settings, '_app_data_dir', return_value=Path(self.temporary.name))
        # The profile-directory test explicitly exercises the real helper below.
        self.real_app_data_dir = settings._app_data_dir
        directory_patch.start(); self.addCleanup(directory_patch.stop)
        self.state = 'stopped'
        self.store = ProfileStore(settings, lambda: self.state, lambda: [{'id': 0, 'label': 'Synthetic input'}])

    def test_profile_lease_prevents_duplicate_host_and_releases_on_close(self):
        first = ProfileLock(self.temporary.name)
        try:
            with self.assertRaisesRegex(BackendError, 'already in use'): ProfileLock(self.temporary.name)
        finally: first.close()
        second = ProfileLock(self.temporary.name)
        second.close()

    def test_private_store_preserves_unknown_values_and_does_not_export_keys(self):
        from desktop_settings import DesktopSettings
        adapter = DesktopSettings(self.store.read, self.store.apply)
        self.assertNotIn('private', str(adapter.snapshot()))
        adapter.save(adapter.snapshot()['revision'], {'bible_translation': 'WEB'})
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['future'], 42)
        self.assertEqual(saved['deepgram_api_key'], 'private')

    def test_store_rechecks_running_state_conflicts_and_corruption(self):
        _, revision = self.store.load()
        self.state = 'running'
        with self.assertRaises(ValueError): self.store.apply({'mic_index': 0}, revision)
        self.state = 'stopped'; self.path.write_text(self.path.read_text()+' ')
        with self.assertRaises(ValueError): self.store.apply({'mic_index': 0}, revision)
        self.path.write_text('{broken')
        with self.assertRaises(ValueError): self.store.load()
        self.assertEqual(self.path.read_text(), '{broken')

    def test_configuration_preserves_engine_guards_and_credentials(self):
        def configure(language='en', mic_index=0, confidence=.75, manual_confirm=True, verify=True,
                      cooldown=3, dedup_window=60, verse_interrupt=False, deepgram_api_key='',
                      local_llm_endpoint='', gcp_credentials_path='', bible_translation='KJV',
                      confirm_request_callback=None, gui_app=None, bot_bridge_enabled=True): pass
        engine = SimpleNamespace(configure=configure)
        values = {**settings.DEFAULTS, 'language': 'Malayalam', 'cooldown': 7, 'verify': False, 'deepgram_api_key': 'private'}
        callback = Mock()
        mapped = configuration(values, settings, engine, callback)
        self.assertEqual(mapped['cooldown'], 7)
        self.assertFalse(mapped['verify'])
        self.assertTrue(mapped['manual_confirm'])
        self.assertEqual(mapped['deepgram_api_key'], 'private')
        self.assertIs(mapped['confirm_request_callback'], callback)
        self.assertEqual(mapped['language'], 'ml')
        self.assertIsNone(mapped['gui_app'])
        self.assertFalse(mapped['bot_bridge_enabled'])
        values['language'] = 'Hindi Nova-3'
        self.assertEqual(configuration(values, settings, engine, callback)['language'], 'hi')

    def test_unsupported_features_and_missing_keys_are_explicit(self):
        for key in ('discord_bot_token', 'settings_sync_url'):
            value = {**settings.DEFAULTS, key: True}
            self.assertIn('migration still needs', start_problem(value))
        self.assertIn('credentials are missing', start_problem(settings.DEFAULTS))
        values = {**settings.DEFAULTS, 'deepgram_api_key': 'present'}
        self.assertEqual(start_problem(values), '')
        self.assertEqual(start_problem({**values, 'local_llm_warm_at_start': True}), '')
        self.assertEqual(start_problem({**values, 'watcher_enabled': True}), '')
        self.assertEqual(start_problem({**values, 'live_points_llm_enabled': True}), '')

    def test_schedule_resolves_at_explicit_start_without_saving_or_changing_guards(self):
        values, _ = self.store.load()
        values.update(smart_schedule=True, language='English', stt_engine='sarvam',
                      sarvam_api_key='private', secondary_stt_engine='assemblyai',
                      assemblyai_api_key='private', dedup_window=91)
        self.path.write_text(json.dumps(values))
        original = self.path.read_bytes()
        publisher = ObserverPublisher(True, self.temporary.name)
        runtime = SimpleNamespace(verification=True, state=Mock(return_value='stopped'), start=Mock(return_value=True),
                                  stop=Mock(), panic=Mock(), thread=None, error='', stop_requested=threading.Event())
        host = BackendHost(settings, publisher, runtime, [{'id': 0, 'label': 'Synthetic input'}])
        self.addCleanup(host.close)
        runtime.start.assert_not_called()
        import datetime
        from service_schedule import effective_start_settings
        saturday = datetime.datetime(2026, 10, 17, 12)
        with patch('desktop_backend.effective_start_settings', side_effect=lambda raw, _: effective_start_settings(raw, saturday)):
            self.assertTrue(host.start())
        effective = runtime.start.call_args.args[0]
        self.assertEqual((effective['language'], effective['secondary_language']), ('Malayalam', 'en'))
        self.assertTrue(effective['dual_stt_enabled'])
        self.assertEqual(effective['dedup_window'], 91)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertIn('Smart Schedule selected Malayalam', host.notice)

    def test_schedule_incompatible_primary_provider_stays_stopped(self):
        values, _ = self.store.load()
        values.update(smart_schedule=True, language='English', stt_engine='deepgram')
        self.path.write_text(json.dumps(values))
        publisher = ObserverPublisher(True, self.temporary.name)
        runtime = SimpleNamespace(verification=True, state=Mock(return_value='stopped'), start=Mock(),
                                  stop=Mock(), panic=Mock(), thread=None, error='', stop_requested=threading.Event())
        host = BackendHost(settings, publisher, runtime, [{'id': 0, 'label': 'Synthetic input'}])
        self.addCleanup(host.close)
        import datetime
        from service_schedule import effective_start_settings
        with patch('desktop_backend.effective_start_settings', side_effect=lambda raw, _: effective_start_settings(raw, datetime.datetime(2026, 10, 17))):
            self.assertFalse(host.start())
        runtime.start.assert_not_called()
        self.assertIn('supported primary language', host.notice)

    def test_host_boot_never_starts_recognition_and_close_stops_only_owned_runtime(self):
        publisher = ObserverPublisher(True, self.temporary.name)
        runtime = SimpleNamespace(verification=True, state=Mock(return_value='stopped'), start=Mock(return_value=True),
                                  stop=Mock(), panic=Mock(), thread=None, error='', stop_requested=threading.Event())
        host = BackendHost(settings, publisher, runtime, [{'id': 0, 'label': 'Synthetic input'}])
        self.addCleanup(publisher.close)
        runtime.start.assert_not_called()
        host.tick()
        self.assertEqual(publisher.snapshot()['host']['verification'], True)
        self.assertTrue(host.close())
        runtime.stop.assert_called_once()

    def test_unexpected_start_error_never_exports_raw_exception(self):
        publisher = ObserverPublisher(True, self.temporary.name)
        runtime = SimpleNamespace(verification=True, state=Mock(return_value='stopped'), start=Mock(side_effect=ValueError('private-key')),
                                  stop=Mock(), panic=Mock(), thread=None, error='', stop_requested=threading.Event())
        host = BackendHost(settings, publisher, runtime, [{'id': 0, 'label': 'Synthetic input'}])
        self.addCleanup(host.close)
        with patch('desktop_backend.logging.getLogger') as logger:
            self.assertFalse(host.start())
            logger.return_value.exception.assert_called_once()
        host.tick()
        self.assertNotIn('private-key', str(publisher.snapshot()))
        self.assertIn('private backend log', host.notice)

    def test_profile_override_isolated_and_legacy_profile_unchanged_when_unset(self):
        with patch.dict(os.environ, {'VERSEVIEW_PROFILE_DIRECTORY': self.temporary.name}):
            self.assertEqual(self.real_app_data_dir(), Path(self.temporary.name))
        with patch.dict(os.environ, {}, clear=True):
            with patch('pathlib.Path.home', return_value=Path(self.temporary.name)/'legacy-home'), patch('pathlib.Path.mkdir'):
                self.assertNotEqual(self.real_app_data_dir(), Path(self.temporary.name))

    def test_settings_module_import_does_not_require_tkinter(self):
        source = Path(settings.__file__).read_text(encoding='utf-8')
        import ast
        tree = ast.parse(source)
        self.assertFalse(any(isinstance(node, ast.Import) and any(alias.name.startswith('tkinter') for alias in node.names)
                             for node in tree.body))


if __name__ == '__main__': unittest.main()
