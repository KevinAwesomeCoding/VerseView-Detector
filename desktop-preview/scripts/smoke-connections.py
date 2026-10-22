"""Native frozen settings/connections acceptance; isolated QA, no microphone/network."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

root=Path(__file__).resolve().parents[1]
backend=Path((root/'backend-build/latest.txt').read_text().strip())
executable=backend/('VerseViewBackend.exe' if os.name=='nt' else 'VerseViewBackend')
with tempfile.TemporaryDirectory(prefix='vv-connections-smoke-') as temporary:
    directory=Path(temporary);profile=directory/'QA/Backend';profile.mkdir(parents=True)
    settings=profile/'settings.json'
    settings.write_text(json.dumps(dict(language='English',stt_engine='deepgram',mic_index=0,deepgram_api_key='SECRET-QA',
        local_llm_host='127.0.0.1',local_llm_port=11434,local_llm_model_verse='qa:model',local_llm_auth_token='SECRET-TOKEN',
        settings_sync_url='',manual_confirm=True,verify=False,auto_save_notes=False,auto_start=False,future={'keep':True})))
    with (directory/'backend.log').open('wb') as log:
        child=subprocess.Popen([str(executable),'--profile',str(profile),'--verify-isolated'],stdin=subprocess.PIPE,stdout=log,stderr=log,text=True,env={**os.environ,'VV_PREVIEW_TEST_PROFILE':'1'})
        def snapshot():return json.loads((profile/'Observer'/f'engine-{child.pid}.json').read_bytes())
        def wait_for(predicate):
            deadline=time.monotonic()+25
            while time.monotonic()<deadline:
                try:
                    value=snapshot()
                    if predicate(value):return value
                except (OSError,ValueError,KeyError,TypeError):pass
                if child.poll() is not None:raise AssertionError('Frozen host exited unexpectedly')
                time.sleep(.05)
            raise AssertionError('Timed out waiting for connection acknowledgement')
        def command(value,action='connection_action',**extra):
            identity=uuid.uuid4().hex;folder=profile/'Observer'/f"control-{child.pid}-{value['control']['id']}"
            request=dict(id=identity,action=action,control_id=value['control']['id'],session_id=value['session_id'],created_at=time.time(),**extra)
            dest=folder/f'command-{identity}.json';temp=dest.with_suffix('.tmp');temp.write_text(json.dumps(request));temp.replace(dest)
            return identity
        def operation(value,op,**extra):return command(value,operation=op,settings_revision=value['control']['settings']['revision'],**extra)
        try:
            value=wait_for(lambda s:s.get('control',{}).get('connections') is not None)
            assert value['control']['connections']['local_targets']['verse']['endpoint']=='http://127.0.0.1:11434'
            operation(value,'local_test',role='verse');value=wait_for(lambda s:s['control']['connections']['busy'])
            assert not {'start','save_settings','clear_memory','generate_notes'}&set(value['control']['actions'])
            value=wait_for(lambda s:s['control']['connections']['status']=='complete')
            assert value['control']['connections']['model']=='qa:model'
            operation(value,'prepare_export',include_credentials=False);value=wait_for(lambda s:bool(s['control']['connections']['export']))
            exported=json.loads((profile/'Exports'/(value['control']['connections']['export']['id']+'.txt')).read_bytes())
            assert 'credentials' not in exported and 'SECRET' not in json.dumps(exported)
            exported['values']['chunk']=2048;exported['values']['cooldown']=4.5
            identity=uuid.uuid4().hex;(profile/'Imports').mkdir(exist_ok=True)
            (profile/'Imports'/(identity+'.json')).write_text(json.dumps(dict(kind='settings',text=json.dumps(exported))))
            operation(value,'import',attachment_id=identity,include_credentials=False)
            value=wait_for(lambda s:s['control']['settings']['values']['chunk']==2048)
            saved=json.loads(settings.read_bytes());assert saved['future']=={'keep':True} and saved['deepgram_api_key']=='SECRET-QA'
            stale=command(value,operation='local_warm',settings_revision='f'*32,role='verse')
            value=wait_for(lambda s:any(r['id']==stale and r['outcome']=='rejected' for r in s['control']['results']))
            assert 'SECRET' not in json.dumps(value)
            child.stdin.close();child.wait(timeout=25);assert child.returncode==0
            print(json.dumps(dict(result='PASS',frozen=True,platform=os.name,typedSettings=True,defaultExportOmitsKeys=True,importRetainsUnknowns=True,staleRevisionRejected=True,recognition='NOT USED',networkAndATEM='SYNTHETIC ONLY')))
        except Exception:
            log.flush();out=root/'test-results';out.mkdir(exist_ok=True);(out/'connections-smoke-failure.log').write_bytes((directory/'backend.log').read_bytes())
            try:(out/'connections-smoke-failure-state.json').write_text(json.dumps(snapshot(),indent=2))
            except (OSError,ValueError):pass
            raise
        finally:
            if child.poll() is None:
                try:child.stdin.close();child.wait(timeout=25)
                except (OSError,ValueError,subprocess.TimeoutExpired):child.kill();child.wait(timeout=10)
