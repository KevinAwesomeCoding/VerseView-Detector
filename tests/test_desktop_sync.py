import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock,MagicMock,patch

import settings as config
from desktop_backend import ProfileStore
from desktop_sync import SettingsSync,SyncError,MAX_BYTES,download_json
from desktop_settings import SettingsError


class SyncTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.profile=Path(temporary.name);self.path=self.profile/'settings.json'
        self.original={**config.DEFAULTS,'deepgram_api_key':'SECRET-OLD-STT','settings_sync_url':'https://sync.invalid/SECRET-URL',
                       'future':{'keep':42},'dedup_window':91,'language':'English'}
        self.path.write_text(json.dumps(self.original));self.original_bytes=self.path.read_bytes()
        self.ready=True
        patcher=patch.object(config,'_app_data_dir',return_value=self.profile);patcher.start();self.addCleanup(patcher.stop)
        self.store=ProfileStore(config,lambda:'stopped',lambda:[])
        self.account=dict(type='service_account',project_id='SECRET-PROJECT',private_key='SECRET-KEY',client_email='test@example.invalid')

    def sync(self,remote=None,fetch=None):
        fetch=fetch or Mock(return_value=remote or {})
        sync=SettingsSync(config,self.store.load,self.store.apply_sync,lambda:self.ready,fetch)
        self.store.blocked=lambda:sync.busy
        self.addCleanup(sync.close)
        return sync,fetch

    def finish(self,sync):
        sync.thread.join(3);self.assertFalse(sync.thread.is_alive());sync.tick();return sync.snapshot()

    def test_allowed_credentials_only_and_unchanged_pulls_do_not_rewrite(self):
        remote=dict(deepgram_api_key='SECRET-NEW-STT',discord_bot_token='SECRET-NEW-BOT',language='Hindi',
                    remote_url='https://wrong.invalid',dedup_window=0,future={'erase':True},gcp_credentials_path='/arbitrary/path')
        sync,fetch=self.sync(remote);sync.start();snapshot=self.finish(sync)
        self.assertEqual(snapshot['status'],'applied');self.assertEqual(snapshot['updated_count'],2)
        saved=json.loads(self.path.read_text());self.assertEqual(saved['deepgram_api_key'],'SECRET-NEW-STT')
        for key in ('language','remote_url','dedup_window','future'):self.assertEqual(saved[key],self.original[key])
        self.assertNotIn('SECRET',str(snapshot));self.assertNotIn('https',str(snapshot))
        written=self.path.read_bytes();mtime=self.path.stat().st_mtime_ns
        sync.start();self.assertEqual(self.finish(sync)['status'],'unchanged')
        self.assertEqual(self.path.read_bytes(),written);self.assertEqual(self.path.stat().st_mtime_ns,mtime)

    def test_cloudflare_credentials_sync_without_activating_or_changing_routes(self):
        initial={**self.original,'free_cloud_enabled':False,
                 'free_cloud_config':{'routes':{'summary':{'provider':'groq','model':'keep-local-choice'}}}}
        self.path.write_text(json.dumps(initial))
        remote={'cloudflare_api_token':'SECRET-CLOUDFLARE-TOKEN','cloudflare_account_id':'a'*32,
                'free_cloud_enabled':True,'free_cloud_config':{'routes':{'summary':{'provider':'gemini'}}}}
        sync,_=self.sync(remote);sync.start();snapshot=self.finish(sync)
        saved=json.loads(self.path.read_text())
        self.assertEqual(snapshot['status'],'applied');self.assertEqual(snapshot['updated_count'],2)
        self.assertEqual(saved['cloudflare_api_token'],remote['cloudflare_api_token'])
        self.assertEqual(saved['cloudflare_account_id'],remote['cloudflare_account_id'])
        self.assertFalse(saved['free_cloud_enabled'])
        self.assertEqual(saved['free_cloud_config'],initial['free_cloud_config'])
        self.assertNotIn('SECRET-',str(snapshot))

    def test_raw_base64_and_url_gcp_transport_stays_private_and_reuses_immutable_file(self):
        payload=base64.b64encode(json.dumps(self.account).encode()).decode()
        for remote in (self.account,{config.GCP_CREDENTIALS_PAYLOAD_KEY:payload},{config.GCP_CREDENTIALS_URL_KEY:'https://sync.invalid/credential'}):
            with self.subTest(transport=list(remote)):
                self.path.write_bytes(self.original_bytes)
                fetch=Mock(side_effect=lambda url,_:copy.deepcopy(self.account if url.endswith('/credential') else remote))
                sync,_=self.sync(fetch=fetch);sync.start();snapshot=self.finish(sync)
                self.assertEqual(snapshot['status'],'applied')
                saved=json.loads(self.path.read_text());credential=Path(saved['gcp_credentials_path'])
                self.assertEqual(credential.parent,self.profile/'credentials');self.assertEqual(json.loads(credential.read_text()),self.account)
                self.assertNotIn(config.GCP_CREDENTIALS_PAYLOAD_KEY,saved);self.assertNotIn(config.GCP_CREDENTIALS_URL_KEY,saved)
                self.assertNotIn('SECRET',str(snapshot));before=credential.read_bytes()
                sync.start();self.assertEqual(self.finish(sync)['status'],'unchanged');self.assertEqual(credential.read_bytes(),before)

    def test_failure_retains_previous_settings_and_credential_bytes(self):
        old=self.profile/'old-credential.json';old.write_text('OLD-PRIVATE-CREDENTIAL')
        values={**self.original,'gcp_credentials_path':str(old)};self.path.write_text(json.dumps(values));original=self.path.read_bytes()
        sync,_=self.sync(self.account)
        with patch.object(config,'save',return_value=False):
            sync.start();self.assertEqual(self.finish(sync)['status'],'failed')
        self.assertEqual(self.path.read_bytes(),original);self.assertEqual(old.read_text(),'OLD-PRIVATE-CREDENTIAL')
        self.assertEqual(list((self.profile/'credentials').glob('sync-*.json')),[])
        self.assertEqual(list((self.profile/'credentials').glob('.sync-*')),[])

    def test_invalid_primary_payload_can_use_existing_secondary_url_transport(self):
        remote={config.GCP_CREDENTIALS_PAYLOAD_KEY:'invalid-base64',config.GCP_CREDENTIALS_URL_KEY:'https://sync.invalid/credential'}
        fetch=Mock(side_effect=[remote,self.account]);sync,_=self.sync(fetch=fetch)
        sync.start();self.assertEqual(self.finish(sync)['status'],'applied');self.assertEqual(fetch.call_count,2)

    def test_conflicting_credential_file_is_retained_without_overwrite(self):
        canonical=json.dumps(self.account,sort_keys=True,ensure_ascii=True,indent=2).encode()
        directory=config.get_managed_gcp_credentials_dir();target=directory/('sync-'+hashlib.sha256(canonical).hexdigest()+'.json')
        target.write_text('Existing different private content')
        sync,_=self.sync(self.account);sync.start();self.assertEqual(self.finish(sync)['status'],'failed')
        self.assertEqual(target.read_text(),'Existing different private content');self.assertEqual(self.path.read_bytes(),self.original_bytes)

    def test_state_and_storage_conflicts_prevent_staged_commit(self):
        for conflict in ('state','storage','invalid-storage'):
            with self.subTest(conflict=conflict):
                self.ready=True;self.path.write_bytes(self.original_bytes)
                sync,_=self.sync({'deepgram_api_key':'SECRET-NEW'})
                sync.start();sync.thread.join(3)
                if conflict=='state':self.ready=False
                elif conflict=='invalid-storage':self.path.write_text('{SECRET incomplete edit')
                else:self.path.write_text(json.dumps({**self.original,'future':'Changed elsewhere'}))
                before=self.path.read_bytes();sync.tick()
                self.assertEqual(sync.snapshot()['status'],'conflict');self.assertEqual(self.path.read_bytes(),before)

    def test_busy_pull_blocks_duplicate_fetch_and_local_settings_save(self):
        entered,release=threading.Event(),threading.Event()
        def fetch(*_):entered.set();release.wait(3);return {'deepgram_api_key':'SECRET-NEW'}
        sync,_=self.sync(fetch=fetch);sync.start()
        try:
            self.assertTrue(entered.wait(1))
            with self.assertRaises(SyncError):sync.start()
            _,revision=self.store.load()
            with self.assertRaises(SettingsError):self.store.apply({'language':'Hindi'},revision)
            self.assertEqual(self.path.read_bytes(),self.original_bytes)
        finally:release.set();self.finish(sync)

    def test_auto_pull_is_opt_in_and_readiness_is_required(self):
        sync,fetch=self.sync({'deepgram_api_key':'SECRET-NEW'})
        self.path.write_text(json.dumps({**self.original,'settings_sync_url':''}))
        sync.auto_start();fetch.assert_not_called();self.assertIsNone(sync.thread)
        self.path.write_bytes(self.original_bytes);self.ready=False
        with self.assertRaises(SyncError):sync.start()
        fetch.assert_not_called();self.ready=True
        sync.auto_start();self.assertEqual(self.finish(sync)['status'],'applied')

    def test_close_discards_result_and_prevents_secondary_download_or_writes(self):
        entered=threading.Event();calls=[]
        def fetch(url,cancelled):
            calls.append(url);entered.set()
            while not cancelled():threading.Event().wait(.01)
            return {config.GCP_CREDENTIALS_URL_KEY:'https://sync.invalid/credential'}
        sync,_=self.sync(fetch=fetch);sync.start();self.assertTrue(entered.wait(1))
        with patch('desktop_sync.logging.getLogger') as logger:
            self.assertTrue(sync.close());sync.tick();logger.assert_not_called()
        self.assertEqual(len(calls),1);self.assertEqual(self.path.read_bytes(),self.original_bytes)
        with self.assertRaises(SyncError):sync.start()

    def test_malformed_downloads_fail_without_exposing_or_writing_payload(self):
        cases=[[],{'deepgram_api_key':{'SECRET':'invalid'}},{'deepgram_api_key':'x'*16385},
               {config.GCP_CREDENTIALS_PAYLOAD_KEY:'SECRET-NOT-BASE64'},
               {config.GCP_CREDENTIALS_URL_KEY:'file:///SECRET'},
               {**self.account,'private_key':42}]
        for remote in cases:
            with self.subTest(remote=type(remote)):
                sync,_=self.sync(fetch=Mock(return_value=remote));sync.start();snapshot=self.finish(sync)
                self.assertEqual(snapshot['status'],'failed');self.assertNotIn('SECRET',str(snapshot))
                self.assertEqual(self.path.read_bytes(),self.original_bytes)

    def test_snapshot_and_startup_failure_tolerate_incomplete_private_json(self):
        sync,_=self.sync();self.path.write_text('{SECRET broken')
        self.assertFalse(sync.snapshot()['configured']);sync.auto_start()
        self.assertEqual(sync.snapshot()['status'],'failed');self.assertNotIn('SECRET',str(sync.snapshot()))

    def test_bounded_transport_uses_existing_tls_timeout_and_rejects_other_schemes(self):
        response=MagicMock();response.__enter__.return_value=response;response.iter_content.return_value=[b'{"deepgram_api_key":"synthetic"}']
        with patch('requests.get',return_value=response) as get,patch('certifi.where',return_value='Test CA'):
            self.assertEqual(download_json('https://sync.invalid/test'),{'deepgram_api_key':'synthetic'})
            get.assert_called_once_with('https://sync.invalid/test',timeout=10,verify='Test CA',stream=True)
            response.iter_content.return_value=[b'x'*(MAX_BYTES+1)]
            with self.assertRaises(SyncError):download_json('https://sync.invalid/test')
            for url in ('file:///tmp/key','https://invalid port','https://host:99999/key'):
                with self.assertRaises(SyncError):download_json(url)


if __name__=='__main__':unittest.main()
