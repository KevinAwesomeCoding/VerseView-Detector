import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace
import threading
from desktop_recovery import SessionRecovery, RecoveryError, sermon_data, MAX_TEXT


def fixture():
    return {'transcript': 'Saved English sermon.', 'transcript_secondary': 'യോഹന്നാൻ മൂന്ന് പതിനാറ്',
            'verse_history': [{'ref': 'John 3:16', 'time': '10:01:00', 'layer': 'PARSER'}],
            'verses_cited': ['John 3:16'], 'current_book': 'John', 'current_chapter': 3, 'current_verse': 16,
            'sermon_anchor': {'book': 'John', 'chapter': 3, 'verse': 16},
            'stream_languages': {'primary': 'en', 'secondary': 'ml'},
            'settings': {'api_key': 'MUST-NOT-SAVE'}, 'stt_log': 'MUST-NOT-SAVE',
            'discord_msg_id': 'MUST-NOT-SAVE', 'pending': ['MUST-NOT-SAVE'], 'queue': ['MUST-NOT-SAVE']}


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.profile = Path(self.directory.name)
        import settings
        directory_patch = patch.object(settings, '_app_data_dir', return_value=self.profile)
        directory_patch.start(); self.addCleanup(directory_patch.stop)
        self.recovery = SessionRecovery(self.profile)

    def test_private_utf8_roundtrip_excludes_settings_logs_and_commands(self):
        self.assertTrue(self.recovery.save(fixture(), 'autosave'))
        raw = self.recovery.path.read_bytes()
        self.assertIn('യോഹന്നാൻ', raw.decode('utf-8'))
        self.assertNotIn(b'MUST-NOT-SAVE', raw)
        if os.name != 'nt': self.assertEqual(self.recovery.path.stat().st_mode & 0o777, 0o600)
        next_host = SessionRecovery(self.profile)
        view = next_host.snapshot()
        self.assertEqual(view['status'], 'available')
        self.assertEqual(view['preview']['languages']['secondary'], 'ml')
        self.assertEqual(view['preview']['references'], ['John 3:16'])
        self.assertNotIn('MUST-NOT-SAVE', str(view))

    def test_pending_decision_blocks_start_and_cannot_be_overwritten(self):
        self.recovery.save(fixture(), 'autosave')
        next_host = SessionRecovery(self.profile)
        original = next_host.path.read_bytes()
        with self.assertRaises(RecoveryError): next_host.for_start()
        with self.assertRaises(RecoveryError): next_host.save(fixture(), 'autosave')
        self.assertEqual(next_host.path.read_bytes(), original)
        next_host.choose(next_host.snapshot()['revision'], True)
        self.assertEqual(next_host.for_start(), sermon_data(fixture()))
        self.assertEqual(next_host.snapshot()['status'], 'staged')
        # A close/crash before Start leaves the original recovery available.
        self.assertEqual(SessionRecovery(self.profile).snapshot()['status'], 'available')

    def test_atomic_failure_retains_last_checkpoint_and_removes_temporary_file(self):
        self.recovery.save(fixture(), 'autosave')
        before = self.recovery.path.read_bytes()
        with patch('desktop_recovery.os.replace', side_effect=OSError('private-path')):
            with self.assertRaisesRegex(RecoveryError, 'previous file was retained'):
                self.recovery.save({**fixture(), 'transcript': 'New text'}, 'stopped')
        self.assertEqual(self.recovery.path.read_bytes(), before)
        self.assertEqual(list(self.recovery.path.parent.glob('.session-*')), [])

    def test_stale_revision_and_external_replacement_invalidate_prepared_restore(self):
        self.recovery.save(fixture(), 'autosave')
        next_host = SessionRecovery(self.profile)
        revision = next_host.snapshot()['revision']
        next_host.choose(revision, True)
        value = json.loads(next_host.path.read_bytes())
        value['data']['transcript'] = 'Changed outside the host'
        next_host.path.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaises(RecoveryError): next_host.for_start()
        with self.assertRaises(RecoveryError): next_host.choose(revision, False)
        self.assertEqual(next_host.snapshot()['status'], 'available')

    def test_external_file_is_retained_while_recording(self):
        self.recovery.started()
        self.recovery.save(fixture(), 'autosave')
        self.recovery.path.write_text('{broken private-data', encoding='utf-8')
        with self.assertRaises(RecoveryError): self.recovery.save(fixture(), 'autosave')
        self.assertEqual(self.recovery.path.read_text(encoding='utf-8'), '{broken private-data')

    def test_discard_does_not_follow_symlink_and_corruption_is_not_exported(self):
        self.recovery.path.parent.mkdir()
        self.recovery.path.write_text('{private-key', encoding='utf-8')
        view = self.recovery.snapshot()
        self.assertEqual(view['status'], 'invalid')
        self.assertNotIn('private-key', str(view))
        self.recovery.choose(view['revision'], False)
        self.assertFalse(self.recovery.path.exists())
        target = self.profile/'original.txt'; target.write_text('Original', encoding='utf-8')
        try: self.recovery.path.symlink_to(target)
        except OSError: return  # Symlink creation is not available in every Windows account.
        view = self.recovery.snapshot()
        self.assertEqual(view['status'], 'invalid')
        with self.assertRaises(RecoveryError): self.recovery.choose(view['revision'], True)
        self.recovery.choose(view['revision'], False)
        self.assertEqual(target.read_text(encoding='utf-8'), 'Original')

    def test_idle_empty_and_malformed_content_do_not_destroy_a_checkpoint(self):
        self.assertFalse(self.recovery.save({}, 'autosave'))
        self.assertFalse(self.recovery.path.exists())
        self.recovery.save(fixture(), 'autosave')
        before = self.recovery.path.read_bytes()
        for changes in [{'current_verse': True}, {'current_chapter': -1}, {'verse_history': ['invalid']},
                        {'transcript': 'x'*(MAX_TEXT+1)}]:
            with self.subTest(changes=list(changes)):
                with self.assertRaises(RecoveryError): self.recovery.save({**fixture(), **changes}, 'autosave')
        self.assertEqual(self.recovery.path.read_bytes(), before)

    def test_preview_is_bounded_without_truncating_saved_content(self):
        self.recovery.save({**fixture(), 'transcript': 'a'*5000}, 'stopped')
        next_host = SessionRecovery(self.profile)
        self.assertEqual(len(next_host.snapshot()['preview']['primary']), 2000)
        next_host.choose(next_host.snapshot()['revision'], True)
        self.assertEqual(len(next_host.for_start()['transcript']), 5000)

    def test_engine_string_context_is_preserved_and_numeric_legacy_context_is_adapted(self):
        string_context = {**fixture(), 'current_chapter': '3', 'current_verse': '17',
                          'sermon_anchor': {'book': 'John', 'chapter': '3', 'verse': '17'}}
        self.recovery.save(string_context, 'autosave')
        next_host = SessionRecovery(self.profile)
        next_host.choose(next_host.snapshot()['revision'], True)
        self.assertEqual(next_host.for_start()['current_chapter'], '3')
        self.assertEqual(next_host.for_start()['current_verse'], '17')
        self.assertEqual(sermon_data(fixture())['current_verse'], '16')
        self.assertIsNone(sermon_data({**fixture(), 'current_verse': ''})['current_verse'])

    def test_runtime_restores_after_configure_before_thread_and_keeps_checkpoint(self):
        from desktop_backend import EngineRuntime
        import settings
        self.recovery.save(fixture(), 'autosave')
        recovery = SessionRecovery(self.profile)
        runtime = EngineRuntime.__new__(EngineRuntime)
        order = []
        runtime.engine = SimpleNamespace(configure=Mock(side_effect=lambda **_: order.append('configure')),
                                        restore_session_snapshot=Mock(side_effect=lambda _: order.append('restore')),
                                        clear_sermon_buffer=Mock())
        runtime.recovery, runtime.publisher, runtime.profile = recovery, Mock(), self.profile
        runtime.thread = runtime.loop = None
        runtime.verification, runtime.stop_requested = False, threading.Event()
        runtime.error = ''
        with patch('desktop_backend.threading.Thread') as worker:
            with self.assertRaises(RecoveryError): runtime.start({'deepgram_api_key': 'private'}, settings, Mock())
            worker.assert_not_called()
            runtime.engine.configure.assert_not_called()
            recovery.choose(recovery.snapshot()['revision'], True)
            before = recovery.path.read_bytes()
            worker.return_value.start.side_effect = lambda: order.append('thread')
            self.assertTrue(runtime.start({'deepgram_api_key': 'private'}, settings, Mock()))
        self.assertEqual(order, ['configure', 'restore', 'thread'])
        runtime.engine.clear_sermon_buffer.assert_not_called()
        runtime.engine.restore_session_snapshot.assert_called_once_with(sermon_data(fixture()))
        self.assertEqual(recovery.path.read_bytes(), before)

    def test_failed_configuration_leaves_staged_recovery_recoverable(self):
        from desktop_backend import EngineRuntime
        import settings
        self.recovery.save(fixture(), 'autosave')
        recovery = SessionRecovery(self.profile)
        recovery.choose(recovery.snapshot()['revision'], True)
        runtime = EngineRuntime.__new__(EngineRuntime)
        runtime.engine = SimpleNamespace(configure=Mock(side_effect=RuntimeError('configuration failed')))
        runtime.recovery = recovery
        runtime.thread = runtime.loop = None
        runtime.stop_requested = threading.Event()
        with patch('desktop_backend.threading.Thread') as worker:
            with self.assertRaises(RuntimeError): runtime.start({'deepgram_api_key': 'private'}, settings, Mock())
            worker.assert_not_called()
        self.assertEqual(recovery.snapshot()['status'], 'staged')
        self.assertEqual(SessionRecovery(self.profile).snapshot()['status'], 'available')
