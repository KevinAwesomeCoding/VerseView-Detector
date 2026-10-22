import copy
import datetime as dt
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import settings
from desktop_setup import project, preview, valid_shortcut
from desktop_settings import project as settings_view, validate_changes, SettingsError
from service_schedule import effective_start_settings, scheduled_language, valid_rules
from observer_feed import ObserverPublisher
from desktop_operator import OperatorTools
from desktop_outline import SessionOutline
from desktop_recovery import SessionRecovery
from desktop_sessions import content
from desktop_notes import SessionNotes
from unittest.mock import Mock

class SetupTests(unittest.TestCase):
    def test_schedule_editor_boundaries_and_no_source_mutation(self):
        rows=[dict(day=0,time='10:00',language='Hindi'),dict(day=0,time='09:00',language='English')]
        values={**settings.DEFAULTS,'smart_schedule':True,'service_schedule':rows,'stt_engine':'gcp'};before=copy.deepcopy(values)
        for hour,minute,language in [(8,59,None),(9,0,'English'),(9,59,'English'),(10,0,'Hindi'),(23,59,'Hindi')]:
            self.assertEqual(scheduled_language(dt.datetime(2026,10,19,hour,minute),rows),language)
        self.assertIsNone(scheduled_language(dt.datetime(2026,10,20,12),rows))
        result,language=effective_start_settings(values,dt.datetime(2026,10,19,12))
        self.assertEqual(language,'Hindi');self.assertTrue(result['dual_stt_enabled']);self.assertEqual(result['secondary_language'],'en')
        self.assertEqual(values,before);self.assertEqual(result['stt_engine'],'gcp')

    def test_timezone_uses_instant_and_reports_unavailable_zone(self):
        rows=[dict(day=0,time='00:00',language='English')]
        instant=dt.datetime(2026,10,19,1,tzinfo=dt.timezone.utc)
        self.assertEqual(scheduled_language(instant,rows,'UTC'),'English')
        self.assertEqual(preview({'smart_schedule':True,'schedule_timezone':'Missing/Unknown','service_schedule':rows})['status'],'invalid')
        self.assertIsNone(scheduled_language(instant,[],'UTC'))

    def test_typed_preferences_validate_and_legacy_auto_start_is_not_projected(self):
        values=settings_view({**settings.DEFAULTS,'mic_index':0,'auto_start':True})
        self.assertNotIn('auto_start',values);self.assertEqual(values['desktop_panic_shortcut'],'Shift+Escape')
        checked=validate_changes({'malayalam_transliteration':True,'desktop_transcript_display':'transliteration','schedule_timezone':'UTC','smart_schedule':True,'service_schedule':[]},values,[])
        self.assertTrue(checked['malayalam_transliteration'])
        for patch in [{'service_schedule':[dict(day=7,time='09:00',language='English')]},{'service_schedule':[dict(day=0,time='09:00',language='English')]*2},{'schedule_timezone':'Missing/Unknown'},{'desktop_panic_shortcut':'Escape'},{'malayalam_transliteration':'yes'},{'desktop_transcript_display':'invent'}]:
            with self.assertRaises(SettingsError):validate_changes(patch,values,[])
        self.assertFalse(valid_rules([dict(day=0,time='24:00',language='English')]))

    def test_shortcut_conflicts_and_safe_binding_grammar(self):
        for value in ['Shift+Escape','Control+Shift+P','Alt+Shift+M','Meta+Shift+P','Shift+F8']:self.assertTrue(valid_shortcut(value),value)
        for value in ['esc','Escape','Shift+A','Control+A','Alt+F4','Control+Shift+I','Meta+Shift+Q','Shift+Control+P','Control+Control+Shift+P']:self.assertFalse(valid_shortcut(value),value)

    def test_start_preview_surfaces_missing_device_provider_key_and_incompatible_schedule(self):
        values={**settings.DEFAULTS,'mic_index':2,'deepgram_api_key':'present'}
        self.assertIn('microphone',preview(values,devices=[{'id':0}])['problem'])
        values['mic_index']=0;values['deepgram_api_key']=''
        self.assertIn('credentials',preview(values,devices=[{'id':0}])['problem'])
        values.update(smart_schedule=True)
        self.assertIn('unsupported',preview(values,dt.datetime(2026,10,17),[{'id':0}])['problem'])

    def test_transliteration_provenance_survives_journal_capture_and_export(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);publisher=ObserverPublisher(True,p/'Observer');publisher.begin({'streams':{'primary':{'enabled':True,'language':'ml'}}})
            try:
                publisher.emit('transcript',stream='primary',text='Daivathinte sneham',is_final=True,text_kind='transliteration')
                runtime=SimpleNamespace(profile=p,engine=SimpleNamespace(set_delivery_mode=Mock()),publisher=publisher,has_started=True,recovery=SessionRecovery(p),outline=SessionOutline(),session_snapshot=lambda:{'transcript':'English context','stream_languages':{'primary':'ml'}})
                runtime.operator=OperatorTools(runtime);capture=content(runtime.operator.capture())
                self.assertTrue(capture['speech_transliterated']['primary']);self.assertIn('[Provider transliteration]',capture['speech']['primary'])
                exported=SessionNotes.transcript(capture,'a'*32)
                self.assertIn('contains labeled transliteration',exported);self.assertIn('Daivathinte sneham',exported)
            finally:publisher.close()

if __name__=='__main__':unittest.main()
