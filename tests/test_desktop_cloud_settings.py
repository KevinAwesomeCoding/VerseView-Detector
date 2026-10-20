import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import settings as config
from desktop_backend import ProfileStore
from desktop_settings import DesktopSettings, SettingsError
from desktop_cloud_settings import project_cloud, validate_cloud


class CloudSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'settings.json'
        self.path.write_text(json.dumps({**config.DEFAULTS,'mic_index':0,
            'groq_api_key':'DO-NOT-EXPORT','future':{'keep':True},
            'free_cloud_config':{'future_option':7,'routes':{'translation':{'provider':'groq','model':'qwen/qwen3.8-27b'}}}}))
        p=patch.object(config,'_settings_path',return_value=self.path);p.start();self.addCleanup(p.stop)
        self.store=ProfileStore(config,lambda:'stopped',lambda:[{'id':0,'label':'Test mic'}])
        self.form=DesktopSettings(self.store.read,self.store.apply)

    def test_write_only_credentials_and_routing_preserve_other_settings(self):
        snapshot=self.form.snapshot();self.assertNotIn('DO-NOT-EXPORT',json.dumps(snapshot))
        change={k:v for k,v in snapshot['cloud'].items() if k!='credentials'}
        change.update(enabled=True,confirmed=['groq','gemini','cloudflare'],
                      credentials={'gemini_api_key':'NEW-PRIVATE-KEY'},watcher_min_gap=30)
        self.form.save(snapshot['revision'],{'cloud_settings':change})
        saved=json.loads(self.path.read_text())
        self.assertEqual(saved['gemini_api_key'],'NEW-PRIVATE-KEY')
        self.assertEqual(saved['groq_api_key'],'DO-NOT-EXPORT')
        self.assertEqual(saved['future'],{'keep':True})
        self.assertEqual(saved['free_cloud_config']['future_option'],7)
        self.assertIn('translation',saved['free_cloud_config']['routes'])
        self.assertEqual(saved['free_cloud_config']['watcher_min_gap'],30)
        self.assertTrue(saved['manual_confirm'])
        self.assertTrue(self.form.snapshot()['cloud']['credentials']['gemini_api_key'])
        self.assertNotIn('NEW-PRIVATE-KEY',json.dumps(self.form.snapshot()))

    def test_invalid_patch_never_echoes_secrets_or_writes(self):
        before=self.path.read_bytes()
        patches=[{'credentials':{'gemini_api_key':'SECRET\nBAD'}},
                 {'credentials':{'discord_bot_token':'SECRET'}},
                 {'routes':{'summary':'gemini|paid-model'}},
                 {'enabled':True,'confirmed':[]},
                 {'limits':{'groq':{'rpd':1001,'tpd':200000}}},
                 {'sync_url':'https://user:SECRET@drive.google.com/uc?export=download&id=abcdefghijk'},
                 {'sync_url':'https://drive.google.com/uc?export=download&id=abcdefghijk&token=SECRET'},
                 {'sync_url':'https://other.example/SECRET'},
                 {'watcher_min_gap':float('nan')}]
        for change in patches:
            with self.subTest(change=list(change)):
                with self.assertRaises(SettingsError) as ctx:
                    self.form.save(self.form.snapshot()['revision'],{'cloud_settings':change})
                self.assertNotIn('SECRET',str(ctx.exception))
                self.assertEqual(before,self.path.read_bytes())

    def test_stale_and_running_requests_do_not_write(self):
        revision=self.form.snapshot()['revision']
        data=json.loads(self.path.read_text());data['external']=True;self.path.write_text(json.dumps(data))
        with self.assertRaises(SettingsError):self.form.save(revision,{'cloud_settings':{'watcher_min_gap':30}})
        self.form.refresh();self.store.state=lambda:'running'
        with self.assertRaises(SettingsError):self.form.save(self.form.snapshot()['revision'],{'cloud_settings':{'watcher_min_gap':30}})

    def test_drive_url_saves_without_credentials_or_route_changes(self):
        url='https://drive.google.com/uc?export=download&id=abcdefghijk'
        raw=json.loads(self.path.read_text());before=raw['free_cloud_config']
        checked=validate_cloud({'sync_url':url},raw)
        self.assertEqual(checked['settings_sync_url'],url)
        self.assertNotIn('groq_api_key',checked)
        self.assertEqual(checked['free_cloud_config']['routes']['translation'],before['routes']['translation'])
        self.assertEqual(project_cloud({**raw,**checked})['sync_url'],url)
