import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from desktop_notes import SessionNotes, NotesError
from desktop_operator import OperatorTools
from desktop_recovery import SessionRecovery
from desktop_outline import SessionOutline
from observer_feed import ObserverPublisher


class NotesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.profile=Path(self.temp.name);self.state='stopped'
        self.raw={'transcript':'Engine context. '*30,'transcript_secondary':'Translated engine context. '*15,
                  'verses_cited':['John 3:16','John 3:17'],'verse_history':[{'ref':'John 3:16','time':'12:00','layer':'speech'}],
                  'current_book':'John','current_chapter':'3','current_verse':'17','stream_languages':{'primary':'en','secondary':'ml'}}
        engine=SimpleNamespace(_local_llm_active_for=lambda role:False,_free_cloud_router=None,
            mistral_client=object(),generate_sermon_summary=Mock(return_value='Sermon notes — മലയാളം'),
            send_sermon_notes_to_discord=Mock(),
            set_delivery_mode=Mock(),reset_desktop_memory=Mock())
        publisher=ObserverPublisher(True,self.profile/'Observer');publisher.begin({'streams':{'primary':{'enabled':True,'language':'en'},'secondary':{'enabled':True,'language':'ml'}}});self.addCleanup(publisher.close)
        self.runtime=SimpleNamespace(profile=self.profile,engine=engine,publisher=publisher,verification=False,has_started=True,
            recovery=SessionRecovery(self.profile),outline=SessionOutline(),state=lambda:self.state,
            session_snapshot=lambda:copy.deepcopy(self.raw),suggestions=SimpleNamespace(prepare=Mock()),
            verses=SimpleNamespace(context=lambda:{'revision':'b'*32},reset_context=Mock()))
        self.runtime.operator=OperatorTools(self.runtime)
        self.notes=self.runtime.notes=SessionNotes(self.runtime)
        self.addCleanup(lambda:self.notes.worker and self.notes.worker.join(3))
        publisher.emit('transcript',stream='primary',text='ORIGINAL BEGINNING '+('full original speech '*180),is_final=True)
        publisher.emit('transcript',stream='secondary',text='മലയാളം ആരംഭം '+('സാക്ഷ്യം '*120),is_final=True)
        publisher.flush()

    def generate(self):
        self.notes.generate(self.notes.revision);self.notes.worker.join(3)
        self.assertEqual(self.notes.status,'ready')

    def test_generation_uses_fixed_full_original_bilingual_snapshot_and_posts_notes(self):
        self.generate()
        payload=self.runtime.engine.generate_sermon_summary.call_args.args[0]
        self.assertTrue(payload['transcript'].startswith('ORIGINAL BEGINNING'))
        self.assertGreater(len(payload['transcript']),2000)
        self.assertIn('മലയാളം ആരംഭം',payload['transcript_secondary'])
        self.assertEqual(payload['verses_cited'],['John 3:16','John 3:17'])
        self.assertEqual(self.runtime.engine.generate_sermon_summary.call_args.kwargs,dict(notify=False,strict=True))
        self.runtime.engine.send_sermon_notes_to_discord.assert_called_once_with('Sermon notes — മലയാളം')
        self.assertEqual(len(list((self.profile/'SessionLibrary').glob('*.json'))),1)
        restored=SessionNotes(self.runtime);self.assertEqual(restored.result['text'],'Sermon notes — മലയാളം')

    def test_empty_stale_and_concurrent_generation_never_make_extra_calls(self):
        with self.assertRaises(NotesError):self.notes.generate('a'*32)
        entered,release=threading.Event(),threading.Event();self.addCleanup(release.set)
        def slow(snapshot,**kwargs):entered.set();release.wait(2);return 'Captured only'
        self.runtime.engine.generate_sermon_summary.side_effect=slow
        self.notes.generate(self.notes.revision);self.assertTrue(entered.wait(1))
        with self.assertRaises(NotesError):self.notes.generate(self.notes.revision)
        self.notes.cancel();release.set();self.notes.worker.join(2)
        self.assertEqual(self.notes.status,'cancelled');self.assertIsNone(self.notes.result)
        self.assertEqual(self.runtime.engine.generate_sermon_summary.call_count,1)
        self.runtime.operator.capture=Mock(return_value={'data':{},'speech':{},'outline':''})
        with self.assertRaisesRegex(NotesError,'100'):self.notes.generate(self.notes.revision)

    def test_provider_error_preserves_previous_notes_and_cannot_export_private_exception(self):
        self.generate();before=copy.deepcopy(self.notes.result)
        self.runtime.engine.generate_sermon_summary.side_effect=ValueError('SECRET-PROVIDER-ENDPOINT')
        self.notes.generate(self.notes.revision);self.notes.worker.join(2)
        self.assertEqual(self.notes.status,'failed');self.assertEqual(self.notes.result,before)
        self.assertNotIn('SECRET',str(self.notes.snapshot()))

    def test_exports_keep_full_unicode_and_use_notes_snapshot_after_later_speech(self):
        self.generate();source=self.notes.result['source_id']
        self.runtime.publisher.emit('transcript',stream='primary',text='LATER NEW SPEECH',is_final=True)
        self.notes.prepare_export(self.notes.revision,'all')
        value=self.notes.export;data=(self.profile/'Exports'/(value['id']+'.txt')).read_text(encoding='utf-8')
        self.assertIn('ORIGINAL BEGINNING',data);self.assertIn('മലയാളം ആരംഭം',data);self.assertIn('John 3:17',data)
        self.assertNotIn('LATER NEW SPEECH',data);self.assertEqual(value['source_id'],source)
        self.notes.prepare_export(self.notes.revision,'transcript')
        self.assertIn('LATER NEW SPEECH',(self.profile/'Exports'/(self.notes.export['id']+'.txt')).read_text(encoding='utf-8'))
        self.assertEqual(len(list((self.profile/'Exports').glob('*.txt'))),1)
        with self.assertRaises(NotesError):self.notes.prepare_export('bad','notes')
        with self.assertRaises(NotesError):self.notes.prepare_export(self.notes.revision,'../../secret')

    def test_known_incomplete_original_journal_is_never_exported_as_complete(self):
        self.runtime.publisher.emit('transcript',stream='primary',text='x'*32769,is_final=True)
        with self.assertRaisesRegex(NotesError,'incomplete'):self.notes.prepare_export(self.notes.revision,'transcript')
        self.assertIsNone(self.notes.export)

    def test_auto_save_writes_both_streams_before_optional_notes_and_reuses_same_result(self):
        self.notes.on_stop(False)
        transcript=Path(self.notes.auto['transcript_path']).read_text(encoding='utf-8')
        self.assertIn('മലയാളം ആരംഭം',transcript);self.assertIn('ORIGINAL BEGINNING',transcript)
        self.runtime.engine.generate_sermon_summary.assert_not_called()
        self.generate();calls=self.runtime.engine.generate_sermon_summary.call_count
        self.notes.on_stop(True)
        if self.notes.worker:self.notes.worker.join(2)
        self.assertEqual(self.notes.auto['status'],'saved')
        self.assertEqual(Path(self.notes.auto['notes_path']).read_text(encoding='utf-8'),'Sermon notes — മലയാളം')
        self.assertEqual(self.runtime.engine.generate_sermon_summary.call_count,calls)
        self.runtime.engine.send_sermon_notes_to_discord.assert_called_once()

    def test_auto_save_failure_retains_transcript_and_no_retry_is_scheduled(self):
        self.runtime.engine.generate_sermon_summary.side_effect=ValueError('SECRET')
        self.notes.on_stop(True);self.notes.worker.join(2);self.notes.tick()
        self.assertEqual(self.notes.auto['status'],'failed')
        self.assertTrue(Path(self.notes.auto['transcript_path']).exists());self.assertIsNone(self.notes.pending_auto)
        self.assertEqual(self.runtime.engine.generate_sermon_summary.call_count,1)

    def test_memory_reset_requires_stop_and_backup_then_retains_archives_notes_and_diagnostics(self):
        self.generate();self.state='running'
        with self.assertRaises(NotesError):self.notes.prepare_clear()
        self.state='stopped';self.notes.prepare_clear();revision=self.notes.review['revision']
        self.notes.clear_memory(revision)
        self.runtime.engine.reset_desktop_memory.assert_called_once()
        self.assertFalse(self.runtime.has_started);self.assertIsNone(self.notes.result)
        rows=self.runtime.operator.library.snapshot()['rows'];backup=next(r for r in rows if r['reason']=='before memory clear')
        value=self.runtime.operator.library.restore_content(backup['id'],backup['revision'])
        self.assertEqual(value['notes'],'Sermon notes — മലയാളം');self.assertIn('ORIGINAL BEGINNING',value['speech']['primary'])
        self.assertTrue(list((self.profile/'Diagnostics').glob('before-clear-*.json')))
        self.assertTrue(list((self.profile/'Observer').glob('transcript-*.jsonl')))
        self.assertEqual(self.runtime.publisher.snapshot()['transcripts'],[])
        self.notes.restore(value['notes'],value);self.assertEqual(self.notes.result['text'],value['notes'])

    def test_new_session_saves_current_work_then_clears_context(self):
        self.generate()
        previous_session = self.runtime.publisher.snapshot()['session_id']
        self.notes.new_session()
        backup = next(row for row in self.runtime.operator.library.snapshot()['rows'] if row['reason'] == 'before new session')
        restored = self.runtime.operator.library.restore_content(backup['id'], backup['revision'])
        self.assertEqual(restored['notes'], 'Sermon notes — മലയാളം')
        self.assertIn('ORIGINAL BEGINNING', restored['speech']['primary'])
        self.runtime.engine.reset_desktop_memory.assert_called_once()
        self.assertFalse(self.runtime.has_started)
        self.assertIsNone(self.notes.result)
        self.assertEqual(self.runtime.recovery.snapshot()['status'], 'none')
        self.assertNotEqual(self.runtime.publisher.snapshot()['session_id'], previous_session)

    def test_new_session_keeps_working_memory_if_backup_fails(self):
        with patch.object(self.runtime.operator.library, 'save', side_effect=OSError('Disk unavailable')):
            with self.assertRaises(OSError): self.notes.new_session()
        self.runtime.engine.reset_desktop_memory.assert_not_called()
        self.assertTrue(self.runtime.has_started)

    def test_new_session_can_reset_an_empty_session_without_creating_an_empty_save(self):
        self.runtime.has_started = False
        self.runtime.publisher.begin({'streams': {}})
        self.runtime.operator.capture = Mock(return_value={'data': {}, 'speech': {'primary': '', 'secondary': ''}, 'outline': '', 'notes': ''})
        self.notes.new_session()
        self.assertFalse(any(row['reason'] == 'before new session' for row in self.runtime.operator.library.snapshot()['rows']))
        self.runtime.engine.reset_desktop_memory.assert_called_once()

    def test_stale_review_and_save_failure_do_not_reset_working_memory(self):
        self.notes.prepare_clear();revision=self.notes.review['revision']
        self.raw['current_verse']='18'
        with self.assertRaises(NotesError):self.notes.clear_memory(revision)
        self.notes.prepare_clear();revision=self.notes.review['revision']
        with patch.object(self.runtime.operator.library,'save',side_effect=OSError('Disk unavailable')):
            with self.assertRaises(OSError):self.notes.clear_memory(revision)
        self.runtime.engine.reset_desktop_memory.assert_not_called()
        self.assertEqual(self.raw['current_verse'],'18')

    def test_interrupted_state_is_visible_and_never_automatically_retried(self):
        self.generate();value=json.loads(self.notes.path.read_text(encoding='utf-8'));value['status']='generating';self.notes.path.write_text(json.dumps(value),encoding='utf-8')
        loaded=SessionNotes(self.runtime)
        self.assertEqual(loaded.status,'interrupted');self.assertEqual(loaded.result['text'],self.notes.result['text'])
        self.assertFalse(loaded.busy);self.assertIsNone(loaded.pending_auto)

if __name__=='__main__':unittest.main()
