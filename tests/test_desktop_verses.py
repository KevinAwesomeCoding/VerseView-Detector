import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from desktop_verses import VerseTools, VerseError, reference, exact_chapter


class VerseToolsTests(unittest.TestCase):
    def setUp(self):
        self.state='stopped';self.code='kjv'
        self.engine=SimpleNamespace(current_book=None,current_chapter=None,current_verse=None,BIBLE_TRANSLATION='kjv',
            WORSHIP_MODE=False,DELIVERY_HOLD=False,_delivery_epoch=0,_controller=object(),
            _reject_verse_out_of_range=lambda ref:int(ref.rsplit(':',1)[1])>36,
            get_delivery_events=lambda:[],get_verse_history=lambda:[],deliver_verse=Mock(return_value=True))
        self.engine.set_context=Mock(side_effect=self.context)
        self.engine.set_delivery_mode=Mock(side_effect=lambda **kw:setattr(self.engine,'_delivery_epoch',self.engine._delivery_epoch+1))
        self.runtime=SimpleNamespace(engine=self.engine,state=lambda:self.state,stop_requested=threading.Event(),has_started=False,recovery=SimpleNamespace(staged=None,record=None))
        self.lookup=Mock(return_value=[{'num':n,'text':f'Fixture verse {n}'} for n in range(1,37)])
        self.tools=VerseTools(self.runtime,self.lookup);self.tools.translation=lambda:self.code
        self.addCleanup(self.tools.join)

    def context(self,book,chapter,verse):
        self.engine.current_book,self.engine.current_chapter,self.engine.current_verse=book,chapter,verse

    def preview(self,value='John 3:16'):
        self.tools.preview(value);self.tools.lookup_worker.join(2)
        return self.tools.snapshot()['selected']

    def test_reference_validation_exact_aliases_unique_prefixes_and_ambiguous_or_range_rejection(self):
        for typed,expected in [('gen 3 2','Genesis 3:2'),('1pe 3:8','1 Peter 3:8'),('John chapter 3 verse 16','John 3:16'),('Song of Solomon 1:2','Song of Solomon 1:2')]:
            self.assertEqual(reference(self.engine,typed,True)[0],expected)
        for invalid in ['J 3:16','John 0:16','John 22:1','John 3:0','John 3:37','John 3:16-17','John 3:16; Luke 4:1','../../x 3:16','John 3',None]:
            with self.assertRaises(VerseError,msg=str(invalid)):reference(self.engine,invalid,True)

    def test_stopped_context_stages_for_start_without_presentation_and_live_context_invalidates_old_delivery(self):
        self.tools.set_context(self.tools.context()['revision'],'John 3:16')
        self.engine.set_context.assert_not_called();self.engine.deliver_verse.assert_not_called()
        self.assertTrue(self.tools.context()['staged']);self.tools.prepare_start()
        self.engine.set_context.assert_called_once_with(book='John',chapter='3',verse='16')
        self.state='running';self.tools.set_context(self.tools.context()['revision'],'John 4')
        self.engine.set_delivery_mode.assert_called_once_with(worship=False,hold=False)
        self.assertEqual(self.engine.current_chapter,'4');self.assertEqual(self.engine.current_verse,'')
        self.engine.deliver_verse.assert_not_called()

    def test_speech_changes_context_revision_and_stale_edits_do_not_mutate_it(self):
        rev=self.tools.context()['revision'];self.engine.current_book='Luke'
        with self.assertRaisesRegex(VerseError,'changed'):self.tools.set_context(rev,'John 3:16')
        self.engine.set_context.assert_not_called()

    def test_chapter_paging_and_history_selection_are_read_only(self):
        self.tools.preview('John 3',chapter=True);self.tools.lookup_worker.join(2)
        self.assertEqual(len(self.tools.snapshot()['chapter']['rows']),8)
        self.assertTrue(self.tools.snapshot()['chapter']['more'])
        self.tools.preview('John 3',chapter=True,page=1);self.tools.lookup_worker.join(2)
        self.assertEqual(self.tools.snapshot()['chapter']['rows'][0]['reference'],'John 3:9')
        self.lookup.assert_called_once_with('John','3','kjv')
        self.engine.get_verse_history=lambda:[{'ref':'John 3:16','time':'12:00:00'}]
        self.assertEqual(self.tools.snapshot()['history'][0]['reference'],'John 3:16')
        self.preview();self.engine.deliver_verse.assert_not_called();self.engine.set_context.assert_not_called()

    def test_explicit_send_requires_current_selection_running_state_and_preserves_guards(self):
        selected=self.preview()
        with self.assertRaises(VerseError):self.tools.send(selected['id'])
        self.state='running';self.tools.send(selected['id']);self.tools.send_worker.join(2)
        self.engine.deliver_verse.assert_called_once()
        args,kw=self.engine.deliver_verse.call_args
        self.assertEqual(args[0],'John 3:16');self.assertFalse(kw['bypass_cooldown']);self.assertEqual(kw['expected_epoch'],0)
        self.assertEqual(kw['source'],'DESKTOP-MANUAL');self.engine.set_context.assert_not_called()
        self.preview('John 3:17')
        with self.assertRaises(VerseError):self.tools.send(selected['id'])

    def test_translation_changes_or_stop_discard_late_preview_and_block_stale_send(self):
        entered,release=threading.Event(),threading.Event();self.addCleanup(release.set)
        self.tools.lookup=lambda *args:(entered.set(),release.wait(2),[{'num':16,'text':'Old translation'}])[-1]
        self.tools.preview('John 3:16');self.assertTrue(entered.wait(2));self.code='web'
        release.set();self.tools.lookup_worker.join(2)
        selected=self.tools.snapshot()['selected'];self.assertEqual(selected['status'],'stale');self.assertEqual(selected['text'],'')
        self.state='running'
        with self.assertRaises(VerseError):self.tools.send(selected['id'])
        self.tools.cancel();self.assertEqual(self.tools.selected['status'],'stale')

    def test_text_failure_leaves_validated_reference_without_fabricated_text(self):
        self.lookup.return_value=[];selected=self.preview()
        self.assertEqual(selected['status'],'unavailable');self.assertEqual(selected['text'],'')
        self.engine.deliver_verse.assert_not_called()
        self.code='niv'
        with patch('bible_fetcher._fetch_chapter_helloao',return_value=[]),patch('bible_fetcher._fetch_chapter_bible_api_com') as fallback:
            self.assertEqual(exact_chapter('John','3','niv'),[]);fallback.assert_not_called()

    def test_corrupt_oversized_and_duplicate_lookup_rows_do_not_enter_the_feed(self):
        self.lookup.return_value=[{'num':16,'text':'Valid'}, {'num':16,'text':'Duplicate'}, {'num':999,'text':'Invalid'}, {'num':17,'text':'x'*6001}]
        self.tools.preview('John 3',chapter=True);self.tools.lookup_worker.join(2)
        self.assertEqual(self.tools.chapter['rows'],[{'reference':'John 3:16','text':'Valid'}])
        self.lookup.return_value='not a chapter';self.code='web';self.preview('John 3:16')
        self.assertEqual(self.tools.selected['status'],'unavailable')
