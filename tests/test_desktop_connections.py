import copy
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import uuid
import settings
from desktop_backend import ProfileStore
from desktop_connections import Connections, ConnectionError
from desktop_settings import DesktopSettings, project, validate_changes, SettingsError
from desktop_options import validate_secrets, valid


class ConnectionsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.path=self.root/'settings.json';self.values={**settings.DEFAULTS,'mic_index':0,'deepgram_api_key':'SECRET-ORIGINAL','future':{'retain':True},'local_llm_model_verse':'custom:verse'};self.path.write_text(json.dumps(self.values))
        for target,name,value in [(settings,'_settings_path',lambda:self.path),(settings,'_app_data_dir',lambda:self.root)]:
            p=patch.object(target,name,value);p.start();self.addCleanup(p.stop)
        self.state='stopped';self.store=ProfileStore(settings,lambda:self.state,lambda:[{'id':0,'label':'QA mic'}]);self.adapter=DesktopSettings(self.store.read,self.store.apply)
        self.engine=SimpleNamespace(test_local_llm_connection=Mock(return_value=(True,'SECRET-PRIVATE')),warm_local_llm_model=Mock(return_value=(True,'SECRET-PRIVATE')))
        self.runtime=SimpleNamespace(profile=self.root,state=lambda:self.state,notes=SimpleNamespace(busy=False,pending_auto=False),warmup=SimpleNamespace(thread=None),bot=SimpleNamespace(snapshot=lambda:{'status':'stopped'}),engine=self.engine,verification=False,has_started=True)
        self.c=Connections(self.runtime,self.store,self.adapter);self.addCleanup(lambda:self.c.worker and self.c.worker.join(2))
    def revision(self):self.adapter.refresh();return self.adapter.snapshot()['revision']
    def attachment(self,kind,text):
        key=uuid.uuid4().hex;folder=self.root/'Imports';folder.mkdir(exist_ok=True);(folder/(key+'.json')).write_text(json.dumps(dict(kind=kind,text=text)));return key
    def test_local_probe_captures_effective_model_and_hides_private_reply(self):
        self.c.run('local_test',self.revision(),'verse');self.c.worker.join(2)
        args=self.engine.test_local_llm_connection.call_args.kwargs
        self.assertEqual(args['model'],'custom:verse');self.assertEqual(self.c.snapshot()['status'],'complete');self.assertNotIn('SECRET',str(self.c.snapshot()))
        self.c.run('local_warm',self.revision(),'watcher');self.c.worker.join(2)
        args=self.engine.warm_local_llm_model.call_args.kwargs;self.assertEqual(args['model'],'custom:verse');self.assertEqual(args['role'],'watcher');self.assertEqual(args['keep_alive'],'30m')
    def test_cancel_discards_late_result_and_busy_work_prevents_overlapping_actions(self):
        entered,release=threading.Event(),threading.Event();self.addCleanup(release.set)
        def probe(**_):entered.set();release.wait(1);return True,'private'
        self.engine.test_local_llm_connection.side_effect=probe;self.c.run('local_test',self.revision());entered.wait(1)
        with self.assertRaises(ConnectionError):self.c.run('local_test',self.revision())
        self.c.cancel();self.assertTrue(self.c.busy);release.set();self.c.worker.join(2)
        self.assertEqual(self.c.snapshot()['status'],'cancelled');self.assertEqual(self.engine.test_local_llm_connection.call_count,1)
    def test_stale_active_notes_and_bot_guards_prevent_network(self):
        for state in ('running','starting','stopping'):
            self.state=state
            with self.assertRaises(ConnectionError):self.c.run('local_test',self.revision())
        self.state='stopped';self.runtime.notes.busy=True
        with self.assertRaises(ConnectionError):self.c.run('local_test',self.revision())
        self.runtime.notes.busy=False
        with self.assertRaises(ConnectionError):self.c.run('local_test','f'*32)
        self.engine.test_local_llm_connection.assert_not_called()
    def test_atem_requires_fresh_settings_bound_target_review_and_isolation(self):
        self.runtime.verification=True
        with self.assertRaises(ConnectionError):self.c.prepare_atem(self.revision())
        self.adapter.save(self.revision(),{'atem_ip':'192.0.2.10'});revision=self.revision();self.c.prepare_atem(revision);review=self.c.snapshot()['atem_review']['id']
        with self.assertRaises(ConnectionError):self.c.run('atem_on',revision,review=review)
        self.c.run('atem_on',revision,review=review,isolated=True);self.c.worker.join(2)
        self.assertIn('Synthetic',self.c.snapshot()['message'])
        with self.assertRaises(ConnectionError):self.c.run('atem_off',revision,review=review,isolated=True)
    def test_export_scope_omits_secrets_by_default_and_persists_original_settings(self):
        self.c.prepare_export(self.revision(),False);packet=self.c.snapshot()['export'];data=json.loads((self.root/'Exports'/(packet['id']+'.txt')).read_text(encoding='utf-8'))
        self.assertNotIn('credentials',data);self.assertNotIn('SECRET',json.dumps(data));self.assertFalse(packet['include_credentials'])
        self.c.prepare_export(self.revision(),True);packet=self.c.snapshot()['export'];data=json.loads((self.root/'Exports'/(packet['id']+'.txt')).read_text(encoding='utf-8'));self.assertEqual(data['credentials']['deepgram_api_key'],'SECRET-ORIGINAL')
        self.assertEqual(json.loads(self.path.read_text(encoding='utf-8')),self.values)
    def test_validated_settings_import_retains_unknown_fields_and_respects_credential_scope(self):
        view=project(self.values);view.update(cooldown=4.5,local_llm_role_verse='local')
        payload=dict(schema=1,kind='verseview-settings',values=view,credentials={'deepgram_api_key':'SECRET-REPLACEMENT','local_llm_auth_token':'SECRET-TOKEN','gladia_api_key':'SECRET-GLADIA'})
        self.c.import_file(self.revision(),self.attachment('settings',json.dumps(payload)),False)
        result=json.loads(self.path.read_text(encoding='utf-8'));self.assertEqual(result['deepgram_api_key'],'SECRET-ORIGINAL');self.assertEqual(result['cooldown'],4.5);self.assertEqual(result['future'],{'retain':True})
        self.c.import_file(self.revision(),self.attachment('settings',json.dumps(payload)),True)
        result=json.loads(self.path.read_text(encoding='utf-8'));self.assertEqual(result['deepgram_api_key'],'SECRET-REPLACEMENT');self.assertEqual(result['local_llm_auth_token'],'SECRET-TOKEN');self.assertEqual(result['gladia_api_key'],'SECRET-GLADIA');self.assertNotIn('SECRET',str(self.c.snapshot()))
    def test_invalid_import_and_atomic_save_failure_preserve_settings_and_remove_new_credential(self):
        before=self.path.read_bytes()
        with self.assertRaises(ConnectionError):self.c.import_file(self.revision(),self.attachment('settings',json.dumps({'schema':1,'kind':'verseview-settings','values':{'remote_url':'file:///secret'}})),False)
        self.assertEqual(before,self.path.read_bytes())
        credential=json.dumps(dict(type='service_account',project_id='QA',private_key='PRIVATE-QA',client_email='qa@example.invalid'))
        with patch.object(settings,'save',return_value=False):
            with self.assertRaises(ValueError):self.c.import_file(self.revision(),self.attachment('gcp',credential),True)
        self.assertEqual(before,self.path.read_bytes());self.assertFalse(list((self.root/'credentials').glob('*.json')))
        self.c.import_file(self.revision(),self.attachment('gcp',credential),True)
        self.assertTrue(self.c.snapshot()['gcp_configured']);self.assertNotIn('PRIVATE-QA',str(self.c.snapshot()))
    def test_probe_failure_never_exposes_provider_reply_or_retries(self):
        self.engine.test_local_llm_connection.return_value=(False,'SECRET raw provider failure')
        self.c.run('local_test',self.revision());self.c.worker.join(2)
        self.assertEqual(self.c.snapshot()['status'],'failed');self.assertNotIn('SECRET',str(self.c.snapshot()))
        self.assertEqual(self.engine.test_local_llm_connection.call_count,1)

    def test_real_local_http_probe_and_role_warm_reuse_engine_transport(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import vv_streaming_master as engine
        requests=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def reply(self,value):
                data=json.dumps(value).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
            def do_GET(self):self.reply({'models':[{'name':'qa:model'}]})
            def do_POST(self):
                data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append((self.path,data,dict(self.headers)))
                self.reply({'choices':[{'message':{'content':'OK'}}],'message':{'content':'OK'},'done':True})
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            url=f'http://127.0.0.1:{server.server_port}'
            args=dict(endpoint=url,model='qa:model',timeout=5,auth_token='SYNTHETIC-TOKEN',extra_headers='{"X-QA":"value"}')
            self.assertTrue(engine.test_local_llm_connection(**args)[0])
            self.assertTrue(engine.warm_local_llm_model(**args,role='verse',keep_alive='30m')[0])
            self.assertEqual(len(requests),2)
            for _,body,headers in requests:
                self.assertEqual(body['model'],'qa:model');self.assertEqual(headers.get('Authorization'),'Bearer SYNTHETIC-TOKEN');self.assertEqual(headers.get('X-QA'),'value')
            self.assertTrue(all('OK' in json.dumps(body) for _,body,_ in requests))
        finally:server.shutdown();server.server_close();worker.join(2)

    def test_typed_developer_options_and_secret_header_validation(self):
        for key,value in [('rate',16000),('chunk',4096),('dedup_window',60),('local_llm_timeout',45),('atem_ip','192.0.2.10')]:self.assertTrue(valid(key,value))
        for key,value in [('rate',True),('chunk',1.5),('dedup_window',0),('cooldown',float('nan')),('local_llm_endpoint','http://token:secret@host/'),('atem_ip','999.1.1.1')]:self.assertFalse(valid(key,value))
        validate_secrets({'local_llm_extra_headers':'{"Authorization":"Bearer test"}'})
        for value in ['[]','{"X":"a\\r\\nb"}']:
            with self.assertRaises(SettingsError):validate_secrets({'local_llm_extra_headers':value})


class LegacyAuditTests(unittest.TestCase):
    def test_all_79_legacy_fields_have_a_current_reviewed_disposition(self):
        import csv
        root=Path(__file__).resolve().parents[1]
        old=list(csv.DictReader(io.StringIO((root/'docs/evidence/legacy-gui-audit/settings.csv').read_text(encoding='utf-8'))))
        current=list(csv.DictReader(io.StringIO((root/'docs/evidence/consumer-settings-audit.csv').read_text(encoding='utf-8'))))
        self.assertEqual(len(old),79);self.assertEqual(len(current),79)
        self.assertEqual({r['key'] for r in old},{r['key'] for r in current})
        for r in current:
            self.assertIn(r['status'],('Implemented','Replaced deliberately','Bounded deliberately'))
            self.assertTrue(r['destination']);self.assertTrue(r['note'])
    def test_legacy_endpoint_resolution_matches_production_without_echoing_embedded_secrets(self):
        from desktop_options import resolved_endpoint
        self.assertEqual(resolved_endpoint({'local_llm_host':'127.0.0.1','local_llm_port':11434}),'http://127.0.0.1:11434')
        self.assertEqual(resolved_endpoint({'local_llm_endpoint':'https://models.invalid/proxy/'}),'https://models.invalid/proxy')
        self.assertEqual(resolved_endpoint({'local_llm_endpoint':'http://key:secret@host/'}),'')

if __name__=='__main__':unittest.main()
