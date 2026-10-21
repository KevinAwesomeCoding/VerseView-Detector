import copy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from desktop_sessions import SessionLibrary
from desktop_recovery import RecoveryError, SessionRecovery
from desktop_operator import OperatorTools
from observer_feed import ObserverPublisher


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.library = SessionLibrary(self.root)
        self.value = {'data': {'transcript': 'English context', 'transcript_secondary': 'Secondary context',
                              'stream_languages': {'primary': 'en', 'secondary': 'ml'}, 'password': 'PRIVATE'},
                      'speech': {'primary': 'Beginning '+('word '*1800)+' end', 'secondary': 'മലയാളം പ്രസംഗം'},
                      'outline': 'Operator notes', 'settings': {'key': 'PRIVATE'}}

    def test_immutable_bilingual_sessions_page_preview_without_secret_or_execution(self):
        first=self.library.save(self.value,'manual');second=self.library.save(self.value,'manual')
        self.assertNotEqual(first['id'],second['id']);self.assertEqual(len(self.library.snapshot()['rows']),2)
        raw=(self.library.directory/(first['id']+'.json')).read_text(encoding='utf-8')
        self.assertNotIn('PRIVATE',raw)
        self.library.preview(first['id']);p=self.library.snapshot()['selected']
        self.assertEqual(p['secondary'],'മലയാളം പ്രസംഗം');self.assertTrue(p['more']);self.assertEqual(p['outline'],'Operator notes')
        revision=p['revision'];self.library.preview(first['id'],4000)
        self.assertEqual(self.library.snapshot()['selected']['primary'],self.value['speech']['primary'][4000:8000])
        self.assertEqual(self.library.restore_content(first['id'],revision)['speech'],self.value['speech'])
        if os.name!='nt': self.assertEqual((self.library.directory/(first['id']+'.json')).stat().st_mode&0o777,0o600)

    def test_archive_is_read_only_and_stale_or_symlink_session_cannot_resume(self):
        archive=self.root/'Sessions';archive.mkdir();(archive/'old.txt').write_text('Legacy transcript',encoding='utf-8')
        self.library.refresh();row=self.library.snapshot()['rows'][0];self.assertFalse(row['resumable'])
        self.library.preview(row['id']);self.assertEqual(self.library.selected['primary'],'Legacy transcript')
        with self.assertRaises(RecoveryError):self.library.restore_content(row['id'],self.library.selected['revision'])
        saved=self.library.save(self.value,'manual');self.library.preview(saved['id']);rev=self.library.selected['revision']
        file=self.library.directory/(saved['id']+'.json');file.write_text(file.read_text(encoding='utf-8')+' ',encoding='utf-8')
        with self.assertRaisesRegex(RecoveryError,'changed'):self.library.restore_content(saved['id'],rev)
        if os.name!='nt':
            file.unlink();file.symlink_to(archive/'old.txt')
            with self.assertRaises(RecoveryError):self.library.preview(saved['id'])
        with self.assertRaises(RecoveryError):self.library.preview('../../settings')

    def test_failed_write_retains_previous_and_invalid_records_are_visible_but_not_resumable(self):
        saved=self.library.save(self.value,'manual');before=(self.library.directory/(saved['id']+'.json')).read_bytes()
        with patch('desktop_sessions.os.replace',side_effect=OSError('disk full')):
            with self.assertRaises(RecoveryError):self.library.save(self.value,'emergency')
        self.assertEqual((self.library.directory/(saved['id']+'.json')).read_bytes(),before)
        (self.library.directory/('a'*32+'.json')).write_text('{broken')
        self.library.refresh();self.assertTrue(any(r['kind']=='invalid' and not r['resumable'] for r in self.library.rows))
        self.assertFalse(list(self.library.directory.glob('.session-*')))

    def test_autosave_updates_one_current_record_and_preserves_explicit_archives(self):
        saved=self.library.save(self.value,'manual')
        first=self.library.save(self.value,'autosave')
        changed=copy.deepcopy(self.value);changed['outline']='Newest outline'
        second=self.library.save(changed,'autosave')
        self.assertEqual(first['id'],second['id']);self.assertEqual(len(self.library.rows),2)
        self.library.preview(second['id']);self.assertEqual(self.library.selected['outline'],'Newest outline')
        self.assertTrue((self.library.directory/(saved['id']+'.json')).exists())

    def test_catalogue_pagination_and_preview_limits(self):
        for _ in range(23):self.library.save(self.value,'manual')
        self.library.refresh(0);self.assertEqual(len(self.library.rows),20);self.assertTrue(self.library.more)
        self.library.refresh(1);self.assertEqual(len(self.library.rows),3);self.assertFalse(self.library.more)
        with self.assertRaises(RecoveryError):self.library.refresh(-1)
        with self.assertRaises(RecoveryError):self.library.preview(self.library.rows[0]['id'],True)

    def runtime(self):
        publisher=ObserverPublisher(True,self.root/'Observer');publisher.begin({'streams':{'primary':{'enabled':True,'language':'en'},'secondary':{'enabled':True,'language':'ml'}}})
        publisher.emit('transcript',stream='primary',text='Original English',is_final=True)
        publisher.emit('transcript',stream='secondary',text='മലയാളം',is_final=True)
        self.addCleanup(publisher.close)
        runtime=SimpleNamespace(profile=self.root,publisher=publisher,engine=SimpleNamespace(set_delivery_mode=Mock()),
            has_started=True,thread=None,state=lambda:'stopped',stop=Mock(),recovery=SessionRecovery(self.root),
            outline=SimpleNamespace(snapshot=lambda:{'text':'Notes','revision':'a'*32},edit=Mock()),session_snapshot=lambda:self.value['data'])
        return runtime

    def test_emergency_blocks_before_stop_saves_originals_and_never_uses_summary(self):
        runtime=self.runtime();events=[]
        runtime.engine.set_delivery_mode.side_effect=lambda **kw:events.append(('mode',kw))
        runtime.stop.side_effect=lambda:events.append(('stop',None))
        op=OperatorTools(runtime);events.clear();op.save(emergency=True);op.worker.join(3)
        self.assertFalse(op.worker.is_alive());self.assertEqual(events[0],('mode',{'worship':False,'hold':True}));self.assertEqual(events[1][0],'stop')
        self.assertEqual(op.status,'saved');self.assertTrue(op.emergency)
        saved=op.library.restore_content(op.saved['id'],op.library.rows[0]['revision'])
        self.assertEqual(saved['speech'],{'primary':'Original English','secondary':'മലയാളം'});self.assertEqual(saved['outline'],'Notes')

    def test_emergency_supersedes_manual_save_without_premature_success(self):
        import threading
        runtime=self.runtime();op=OperatorTools(runtime)
        first_started,first_release,final_started,final_release=[threading.Event() for _ in range(4)]
        self.addCleanup(first_release.set);self.addCleanup(final_release.set)
        def save(value,reason):
            if reason=='manual': first_started.set();first_release.wait(2)
            else: final_started.set();final_release.wait(2)
            return {'id':'a'*32,'saved_at':'2026-10-20T00:00:00+00:00'}
        with patch.object(op.library,'save',side_effect=save):
            op.save();self.assertTrue(first_started.wait(2));op.save(emergency=True)
            first_release.set();self.assertTrue(final_started.wait(2))
            self.assertEqual(op.status,'stopping');self.assertIsNone(op.saved)
            final_release.set();op.worker.join(2);self.assertEqual(op.status,'saved')

    def test_worship_persists_and_failure_does_not_acknowledge_a_changed_mode(self):
        runtime=self.runtime();op=OperatorTools(runtime);op.set_worship(True)
        self.assertTrue(OperatorTools(runtime).worship)
        with patch('desktop_operator.atomic_write',side_effect=RecoveryError('disk full')):
            with self.assertRaises(RecoveryError):op.set_worship(False)
        self.assertTrue(op.worship)

    def test_resume_preserves_current_and_stages_without_starting_or_presenting(self):
        runtime=self.runtime();op=OperatorTools(runtime)
        saved=op.library.save(self.value,'manual');op.library.preview(saved['id'])
        op.resume(saved['id'],op.library.selected['revision'])
        self.assertEqual(len(op.library.rows),2);self.assertEqual(runtime.recovery.for_start()['transcript'],'English context')
        self.assertEqual(op.pending_restore['outline'],'Operator notes');runtime.stop.assert_not_called()
        op.prepare_start(False);self.assertEqual(op.speech_before,self.value['speech']);runtime.outline.edit.assert_called_once()

    def test_recovery_stage_preserves_file_and_start_new_cancels_staged_content(self):
        recovery=SessionRecovery(self.root);recovery.save(self.value['data'],'stopped');before=recovery.path.read_bytes()
        recovery.stage_saved({'transcript':'Different'});self.assertEqual(recovery.path.read_bytes(),before)
        self.assertEqual(recovery.for_start()['transcript'],'Different')
        recovery.choose(recovery.revision,False);self.assertIsNone(recovery.for_start())

    def test_emergency_write_failure_stays_held_and_retains_previous_library(self):
        runtime=self.runtime();op=OperatorTools(runtime);prior=op.library.save(self.value,'manual')
        with patch('desktop_sessions.os.replace',side_effect=OSError('disk full')):
            op.save(emergency=True);op.worker.join(3)
        self.assertEqual(op.status,'failed');self.assertTrue(op.emergency);self.assertIsNone(op.saved)
        self.assertTrue((op.library.directory/(prior['id']+'.json')).exists())

class WatcherModeTests(unittest.TestCase):
    def test_result_in_flight_before_reset_cannot_be_emitted_or_clear_a_new_slot(self):
        import asyncio
        from contextual_watcher import ContextualVerseWatcher, _Snapshot
        # Use a normal watcher and a controlled provider reply, without any transport.
        async def run():
            watcher=ContextualVerseWatcher.__new__(ContextualVerseWatcher)
            watcher._generation=1;watcher._cfg=SimpleNamespace(llm_timeout_sec=2)
            watcher._call_llm=lambda snap:'{"reference":"John 3:16"}'
            watcher._clear_in_flight=Mock();watcher._parse_json=Mock();watcher._record_cycle=Mock()
            snap=_Snapshot('primary','en','Synthetic older input',generation=0)
            await watcher._run_cycle('primary',snap,asyncio.get_running_loop())
            watcher._clear_in_flight.assert_not_called();watcher._parse_json.assert_not_called()
        asyncio.run(run())
