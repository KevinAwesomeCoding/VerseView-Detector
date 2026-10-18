import copy
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

import settings as config
from desktop_settings import DesktopSettings, GuiSettings, SettingsError, project, validate_changes, providers_for, PROVIDERS
from desktop_control import DesktopControl
from observer_feed import ObserverPublisher


class Widget:
    def __init__(self, value='', **properties):
        self.value, self.properties = value, {'values': [], 'state': 'normal', **properties}
    def get(self): return self.value
    def set(self, value): self.value = value
    def delete(self, *_): self.value = ''
    def insert(self, _, value): self.value = value
    def configure(self, **properties): self.properties.update(properties)
    def cget(self, key): return self.properties[key]


class FakeGUI:
    """The production GuiSettings binding, with inert widgets and no device calls."""
    def __init__(self):
        self._running = self._closing = False
        self._s = dict(config.DEFAULTS)
        self.mic_map = {'[0] Built-in test microphone': 0, '[2] USB test microphone': 2}
        for name, value in [('lang_var', 'English'), ('stt_engine_var', 'Deepgram'),
                            ('dual_stt_var', False), ('sec_lang_var', 'Malayalam'),
                            ('sec_engine_var', 'Sarvam AI'), ('mic_var', '[0] Built-in test microphone'),
                            ('bible_var', 'KJV'), ('url_entry', 'http://127.0.0.1:50010/control.html')]:
            setattr(self, name, Widget(value))
        for name in ('stt_engine_menu', 'sec_engine_menu', 'sec_lang_menu', 'ml_raw_cb', 'ml_translit_cb'):
            setattr(self, name, Widget())
        self._set_dual_log_view = Mock()
        self._update_log_headers = Mock()

    def _collect_settings(self):
        provider_code = lambda label: next((code for code, value in PROVIDERS.items() if value == label), 'legacy-invalid')
        return {**self._s, 'language': self.lang_var.get(), 'stt_engine': provider_code(self.stt_engine_var.get()),
                'dual_stt_enabled': self.dual_stt_var.get(),
                'secondary_language': {'English': 'en', 'Malayalam': 'ml', 'Hindi': 'hi'}[self.sec_lang_var.get()] if self.dual_stt_var.get() else None,
                'secondary_stt_engine': provider_code(self.sec_engine_var.get()),
                'mic_index': self.mic_map.get(self.mic_var.get(), 0), 'bible_translation': self.bible_var.get().lower(),
                'remote_url': self.url_entry.get()}


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=getattr(self, 'test_directory', None))
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'settings.json'
        self.path_patch = patch.object(config, '_settings_path', return_value=self.path)
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        self.gui = FakeGUI()
        self.gui._s['deepgram_api_key'] = 'private-key-never-export'
        self.path.write_text(json.dumps({**self.gui._collect_settings(), 'future_option': {'keep': True}}))
        self.binding = GuiSettings(self.gui, config)
        self.settings = DesktopSettings(self.binding.read, self.binding.apply)

    def test_projection_drops_credentials_and_credential_bearing_url(self):
        self.assertNotIn('private-key', str(self.settings.snapshot()))
        self.gui.url_entry.set('http://username:password@localhost/control.html?token=private')
        self.settings.refresh()
        self.assertEqual(self.settings.snapshot()['values']['remote_url'], '')
        self.assertNotIn('password', str(self.settings.snapshot()))

    def test_save_updates_gui_and_disk_preserving_unknown_fields_secrets_and_guards(self):
        revision = self.settings.snapshot()['revision']
        self.settings.save(revision, {'mic_index': 2, 'language': 'Malayalam', 'stt_engine': 'sarvam',
                                     'dual_stt_enabled': True, 'secondary_language': 'en', 'secondary_stt_engine': 'deepgram',
                                     'remote_url': 'https://test-host.local/control.html', 'bible_translation': 'WEB'})
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['future_option'], {'keep': True})
        self.assertEqual(saved['deepgram_api_key'], 'private-key-never-export')
        for field in ('confidence', 'manual_confirm', 'verify', 'cooldown', 'dedup_window'):
            self.assertEqual(saved[field], config.DEFAULTS[field])
        self.assertEqual(saved['bible_translation'], 'web')
        self.assertEqual(self.gui.mic_var.get(), '[2] USB test microphone')
        self.assertEqual(self.gui.stt_engine_var.get(), 'Sarvam AI')
        self.assertNotEqual(self.settings.snapshot()['revision'], revision)

    def test_save_preserves_external_credentials_and_unrelated_gui_drafts(self):
        saved = json.loads(self.path.read_text())
        saved['future_option'] = {'external': 'latest'}
        saved['deepgram_api_key'] = 'external-key'
        self.path.write_text(json.dumps(saved))
        self.gui._s['deepgram_api_key'] = 'unsaved-gui-key'
        self.gui._s['confidence'] = .99
        self.settings.refresh()
        self.settings.save(self.settings.snapshot()['revision'], {'mic_index': 2})
        persisted = json.loads(self.path.read_text())
        self.assertEqual(persisted['deepgram_api_key'], 'external-key')
        self.assertEqual(persisted['future_option'], {'external': 'latest'})
        self.assertEqual(persisted['confidence'], config.DEFAULTS['confidence'])
        self.assertEqual(self.gui._s['deepgram_api_key'], 'unsaved-gui-key')
        self.assertEqual(self.gui._s['confidence'], .99)
        self.assertEqual(self.gui.sec_lang_var.get(), 'Malayalam')
        self.assertEqual(self.gui.sec_engine_var.get(), 'Sarvam AI')

    def test_external_disk_and_unsaved_gui_edits_invalidate_revision(self):
        for edit in ('disk', 'gui'):
            with self.subTest(edit=edit):
                self.settings.refresh()
                old = self.settings.snapshot()['revision']
                if edit == 'disk': self.path.write_text(self.path.read_text() + ' ')
                else: self.gui.bible_var.set('WEB')
                with self.assertRaisesRegex(SettingsError, 'changed elsewhere'):
                    self.settings.save(old, {'mic_index': 2})

    def test_rejects_arbitrary_or_invalid_fields_and_provider_language_pairs(self):
        for changes in ({'deepgram_api_key': 'oops'}, {'manual_confirm': False}, {'mic_index': True},
                        {'mic_index': 99}, {'language': 'Malayalam', 'stt_engine': 'deepgram'},
                        {'dual_stt_enabled': True, 'secondary_language': 'ml', 'secondary_stt_engine': 'assemblyai_pro'},
                        {'remote_url': 'file:///tmp/test'}, {'remote_url': 'http://host/?key=secret'},
                        {'bible_translation': 'unknown'}, {'language': []}):
            with self.subTest(changes=changes):
                with self.assertRaises(SettingsError):
                    self.settings.save(self.settings.snapshot()['revision'], changes)

    def test_unavailable_microphone_may_be_preserved_but_not_newly_selected(self):
        values = self.settings.snapshot()['values']
        values['mic_index'] = 77
        self.assertEqual(validate_changes({'bible_translation': 'WEB'}, values, [])['bible_translation'], 'WEB')
        with self.assertRaises(SettingsError): validate_changes({'mic_index': 88}, values, [])

    def test_failed_save_restores_widgets_and_keeps_original_file(self):
        old_file, old_widgets = self.path.read_bytes(), self.gui._collect_settings()
        with patch.object(config, 'save', return_value=False):
            with self.assertRaisesRegex(SettingsError, 'Previous values were retained'):
                self.settings.save(self.settings.snapshot()['revision'], {'language': 'Malayalam', 'stt_engine': 'sarvam', 'mic_index': 2})
        self.assertEqual(self.path.read_bytes(), old_file)
        self.assertEqual(self.gui._collect_settings(), old_widgets)
        self.assertEqual(self.gui.sec_lang_var.get(), 'Malayalam')

    def test_rollback_preserves_invalid_legacy_widget_labels(self):
        self.gui.stt_engine_var.set('Legacy provider')
        self.settings.refresh()
        with patch.object(config, 'save', return_value=False):
            with self.assertRaises(SettingsError):
                self.settings.save(self.settings.snapshot()['revision'], {'stt_engine': 'deepgram'})
        self.assertEqual(self.gui.stt_engine_var.get(), 'Legacy provider')

    def test_atomic_writer_failure_does_not_truncate_original_settings(self):
        original = self.path.read_bytes()
        with patch.object(config.os, 'replace', side_effect=OSError('isolated write failure')), patch('builtins.print'):
            self.assertFalse(config.save({'future_option': 'replacement'}))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob('.settings-*')), [])

    def test_corrupt_file_is_unavailable_instead_of_overwritten_with_defaults(self):
        self.path.write_text('{broken')
        self.settings.refresh()
        self.assertIsNone(self.settings.snapshot())
        with self.assertRaises(SettingsError): self.settings.save(uuid.uuid4().hex, {'mic_index': 2})
        self.assertEqual(self.path.read_text(), '{broken')

    def test_binding_checks_stopped_state_and_last_disk_revision(self):
        storage_revision = self.binding.read()['storage_revision']
        self.gui._running = True
        with self.assertRaisesRegex(SettingsError, 'Stop'): self.binding.apply({'mic_index': 2}, storage_revision)
        self.gui._running = False
        self.path.write_text(self.path.read_text() + ' ')
        with self.assertRaisesRegex(SettingsError, 'changed elsewhere'): self.binding.apply({'mic_index': 2}, storage_revision)

    def test_settings_reads_stay_on_gui_thread_and_broker_rechecks_state(self):
        publisher = ObserverPublisher(True, self.temporary.name)
        publisher.begin({'streams': {}})
        self.addCleanup(publisher.close)
        main_thread = threading.get_ident()
        def read():
            self.assertEqual(threading.get_ident(), main_thread)
            return self.binding.read()
        settings = DesktopSettings(read, self.binding.apply)
        state = ['stopped']
        broker = DesktopControl(publisher, lambda: state[0], Mock(), Mock(), enabled=True, settings=settings, clock=lambda: 1000)
        self.addCleanup(broker.close)
        request = dict(id=uuid.uuid4().hex, action='save_settings', control_id=broker.control_id,
                       session_id=publisher.snapshot()['session_id'], created_at=1000,
                       settings_revision=settings.snapshot()['revision'], changes={'mic_index': 2})
        state[0] = 'running'
        broker.execute(request)
        self.assertEqual(publisher.snapshot()['control']['results'][-1]['outcome'], 'rejected')
        self.assertEqual(self.gui.mic_var.get(), '[0] Built-in test microphone')
        # Confirmation-worker refresh only reads cached non-secret settings.
        worker = threading.Thread(target=broker.refresh)
        worker.start(); worker.join(1)
        state[0] = 'stopped'
        request['id'] = uuid.uuid4().hex
        broker.execute(request)
        self.assertEqual(publisher.snapshot()['control']['results'][-1]['outcome'], 'saved')
        self.assertEqual(self.gui.mic_var.get(), '[2] USB test microphone')

    def test_catalog_supported_combinations(self):
        self.assertNotIn('deepgram', providers_for('ml'))
        self.assertIn('gcp', providers_for('ml'))
        self.assertNotIn('assemblyai_pro', providers_for('hi'))
        self.assertIn('assemblyai_multilingual', providers_for('multi'))


if __name__ == '__main__': unittest.main()
