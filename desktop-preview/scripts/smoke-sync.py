"""Frozen credential sync with fake download transport and private QA profile."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

root=Path(__file__).resolve().parents[1]
backend=Path((root/'backend-build/latest.txt').read_text(encoding='utf-8').strip())
executable=backend/('VerseViewBackend.exe' if os.name=='nt' else 'VerseViewBackend')
with tempfile.TemporaryDirectory(prefix='vv-sync-smoke-') as temporary:
    directory=Path(temporary);profile=directory/'QA/Backend';profile.mkdir(parents=True)
    path=profile/'settings.json'
    path.write_text(json.dumps(dict(language='English',stt_engine='deepgram',deepgram_api_key='SECRET-OLD-STT',
        discord_bot_token='SECRET-OLD-BOT',settings_sync_url='https://sync.invalid/SECRET/slow',dedup_window=91,
        manual_confirm=True,verify=False,llm_enabled=False,auto_save_notes=False,future={'keep':42},qa_bot_silence=True)),encoding='utf-8')
    child=None
    with (directory/'backend.log').open('wb') as log:
        try:
            child=subprocess.Popen([str(executable),'--profile',str(profile),'--verify-isolated'],stdin=subprocess.PIPE,
                stdout=log,stderr=log,text=True,env={**os.environ,'VV_PREVIEW_TEST_PROFILE':'1'})
            def snapshot():return json.loads((profile/'Observer'/f'engine-{child.pid}.json').read_bytes())
            def wait_for(predicate,timeout=30):
                deadline=time.monotonic()+timeout
                while time.monotonic()<deadline:
                    try:
                        value=snapshot()
                        if predicate(value):return value
                    except (OSError,ValueError,KeyError,TypeError):pass
                    if child.poll() is not None:raise AssertionError('Frozen sync host exited unexpectedly')
                    time.sleep(.1)
                raise AssertionError('Timed out waiting for sync state')
            def command(value,action):
                identity=uuid.uuid4().hex;inbox=profile/'Observer'/f"control-{child.pid}-{value['control']['id']}"
                request=dict(id=identity,control_id=value['control']['id'],session_id=value['session_id'],created_at=time.time(),action=action)
                target=inbox/f'command-{identity}.json';temp=target.with_suffix('.tmp')
                temp.write_text(json.dumps(request),encoding='utf-8');temp.replace(target);return identity
            def set_url(suffix):
                values=json.loads(path.read_text(encoding='utf-8'));values['settings_sync_url']='https://sync.invalid/SECRET/'+suffix
                path.write_text(json.dumps(values),encoding='utf-8')
            value=wait_for(lambda s:s.get('control',{}).get('sync',{}).get('status')=='pulling')
            assert not {'start','start_bot','save_settings'}&set(value['control']['actions'])
            identity=command(value,'start')
            value=wait_for(lambda s:any(r['id']==identity for r in s['control']['results']))
            assert value['control']['state']=='stopped' and not value['transcripts']
            value=wait_for(lambda s:s['control']['sync']['status']=='applied')
            assert value['control']['sync']['updated_count']==3
            saved=json.loads(path.read_text(encoding='utf-8'));credential=Path(saved['gcp_credentials_path'])
            assert saved['deepgram_api_key']=='SECRET-SYNCED-STT' and saved['discord_bot_token']=='SECRET-SYNCED-BOT'
            assert saved['language']=='English' and saved['dedup_window']==91 and saved['future']=={'keep':42}
            assert credential.parent.resolve()==(profile/'credentials').resolve() and credential.exists()
            assert 'SECRET' not in json.dumps(value)
            before=path.read_bytes();command(value,'pull_settings')
            value=wait_for(lambda s:s['control']['sync']['status']=='unchanged');assert path.read_bytes()==before
            command(value,'start');value=wait_for(lambda s:s['control']['state']=='running')
            assert 'pull_settings' not in value['control']['actions']
            identity=command(value,'pull_settings');value=wait_for(lambda s:any(r['id']==identity for r in s['control']['results']))
            assert path.read_bytes()==before
            command(value,'stop');value=wait_for(lambda s:s['control']['state']=='stopped')
            command(value,'start_bot');value=wait_for(lambda s:s['control']['bot']['status']=='online')
            assert 'pull_settings' not in value['control']['actions']
            command(value,'stop_bot');value=wait_for(lambda s:s['control']['bot']['status']=='stopped')
            set_url('failure');before=path.read_bytes();command(value,'pull_settings')
            value=wait_for(lambda s:s['control']['sync']['status']=='failed');assert path.read_bytes()==before
            set_url('slow');command(value,'pull_settings');value=wait_for(lambda s:s['control']['sync']['status']=='pulling')
            edited=json.loads(path.read_text(encoding='utf-8'));edited['future']='Operator correction';path.write_text(json.dumps(edited),encoding='utf-8');before=path.read_bytes()
            value=wait_for(lambda s:s['control']['sync']['status']=='conflict');assert path.read_bytes()==before
            command(value,'pull_settings');value=wait_for(lambda s:s['control']['sync']['status']=='pulling')
            child.stdin.close();child.wait(timeout=30);assert child.returncode==0 and path.read_bytes()==before
            print(json.dumps(dict(result='PASS',frozen=True,autoPullOptIn=True,download='SYNTHETIC - no external requests',
                credentialOnly=True,portableGCP=True,unchangedSkipsWrite=True,runningEngineAndBotBlockPull=True,
                conflictAndFailurePreserveSettings=True,closeDiscardsResult=True,recognition='manual start only with silent QA STT',presentation='NOT USED')))
        except Exception:
            evidence=root/'test-results';evidence.mkdir(exist_ok=True)
            log.flush();(evidence/'sync-smoke-failure.log').write_bytes((directory/'backend.log').read_bytes())
            try:(evidence/'sync-smoke-failure-state.json').write_text(json.dumps(snapshot(),indent=2),encoding='utf-8')
            except (OSError,ValueError):pass
            raise
        finally:
            if child and child.poll() is None:
                try:child.stdin.close();child.wait(timeout=30)
                except (OSError,ValueError,subprocess.TimeoutExpired):child.kill();child.wait(timeout=10)
