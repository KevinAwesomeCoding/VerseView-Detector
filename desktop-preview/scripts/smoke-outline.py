"""Native frozen outline processing/editor checks; no output window or live services."""
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
with tempfile.TemporaryDirectory(prefix='vv-outline-smoke-') as temporary:
    directory=Path(temporary);profile=directory/'QA/Backend';profile.mkdir(parents=True)
    (profile/'settings.json').write_text(json.dumps(dict(language='English',stt_engine='deepgram',deepgram_api_key='SECRET-QA-STT',
        manual_confirm=True,verify=False,llm_enabled=True,auto_save_notes=False,live_points_llm_enabled=True,
        live_points_prompt='Capture only the synthetic spoken material.',local_llm_enabled=True,
        local_llm_role_outline='local',local_llm_model='qa:model')),encoding='utf-8')
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
                    if child.poll() is not None:raise AssertionError('Frozen outline host exited unexpectedly')
                    time.sleep(.1)
                raise AssertionError('Timed out waiting for frozen outline state')
            def command(value,action,**extra):
                identity=uuid.uuid4().hex
                inbox=profile/'Observer'/f"control-{child.pid}-{value['control']['id']}"
                request=dict(id=identity,control_id=value['control']['id'],session_id=value['session_id'],
                             created_at=time.time(),action=action,**extra)
                target=inbox/f'command-{identity}.json';temp=target.with_suffix('.tmp')
                temp.write_text(json.dumps(request),encoding='utf-8');temp.replace(target);return identity
            value=wait_for(lambda s:s.get('control',{}).get('state')=='stopped')
            assert value['control']['outline']['text']==''
            command(value,'start')
            value=wait_for(lambda s:s.get('control',{}).get('outline',{}).get('source')=='model')
            assert 'SYNTHETIC SERMON OUTLINE' in value['control']['outline']['text']
            value=wait_for(lambda s:bool(s['control']['pending']))
            command(value,'reject',candidate_id=value['control']['pending'][0]['candidate_id'])
            value=wait_for(lambda s:s['control']['outline']['status']=='generating')
            old_revision=value['control']['outline']['revision']
            manual='Operator correction retained. മലയാളം കുറിപ്പ്.'
            command(value,'edit_outline',outline_revision=old_revision,outline_text=manual)
            value=wait_for(lambda s:s['control']['outline']['text']==manual)
            value=wait_for(lambda s:'skipped' in s['control']['outline']['message'])
            assert value['control']['outline']['text']==manual
            stale=command(value,'edit_outline',outline_revision=old_revision,outline_text='Stale replacement')
            value=wait_for(lambda s:any(row['id']==stale and row['outcome']=='rejected' for row in s['control']['results']))
            assert 'SECRET-' not in json.dumps(value)
            command(value,'stop');value=wait_for(lambda s:s['control']['state']=='stopped')
            command(value,'start');value=wait_for(lambda s:s['control']['outline']['status']=='generating')
            command(value,'stop')
            value=wait_for(lambda s:s['control']['state']=='stopping')
            value=wait_for(lambda s:s['control']['state']=='stopped')
            assert value['control']['outline']['text']==manual
            child.stdin.write('{"action":"shutdown"}\n');child.stdin.flush();child.wait(timeout=30);assert child.returncode==0
            print(json.dumps(dict(result='PASS',native=os.name,frozen=True,outline='actual loop with fake model completions',
                staleModelReplyRejected=True,staleOperatorRevisionRejected=True,executorDrainedOnStop=True,
                outputWindow='NOT OPENED',microphoneSTT='NOT USED - callback replay',presentation='FAKE CONTROLLER')))
        finally:
            if child and child.poll() is None:
                try:
                    child.stdin.write('{"action":"shutdown"}\n');child.stdin.flush();child.wait(timeout=30)
                except (OSError,subprocess.TimeoutExpired):child.kill();child.wait(timeout=10)
