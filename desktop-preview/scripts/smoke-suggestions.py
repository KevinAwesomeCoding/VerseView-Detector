"""Native frozen watcher -> bounded advice -> operator -> actual guarded delivery.

All speech/model/browser services are explicitly mocked by the QA adapter.
"""
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
with tempfile.TemporaryDirectory(prefix='vv-watcher-smoke-') as temporary:
    directory=Path(temporary);profile=directory/'QA/Backend';profile.mkdir(parents=True)
    values=dict(language='English',stt_engine='deepgram',deepgram_api_key='SECRET-QA-STT',
        sarvam_api_key='SECRET-QA-SARVAM',dual_stt_enabled=True,secondary_language='ml',secondary_stt_engine='sarvam',
        manual_confirm=True,verify=False,llm_enabled=False,auto_save_notes=False,watcher_enabled=True,
        watcher_provider='local',local_llm_enabled=True,local_llm_model='SECRET-QA-MODEL')
    (profile/'settings.json').write_text(json.dumps(values),encoding='utf-8')
    child=None
    with (directory/'backend.log').open('wb') as log:
        try:
            child=subprocess.Popen([str(executable),'--profile',str(profile),'--verify-isolated'],stdin=subprocess.PIPE,
                stdout=log,stderr=log,text=True,env={**os.environ,'VV_PREVIEW_TEST_PROFILE':'1'})
            def snapshot():
                return json.loads((profile/'Observer'/f'engine-{child.pid}.json').read_bytes())
            def wait_for(predicate,timeout=30):
                deadline=time.monotonic()+timeout
                while time.monotonic()<deadline:
                    try:
                        value=snapshot()
                        if predicate(value):return value
                    except (OSError,ValueError,KeyError,TypeError):pass
                    if child.poll() is not None:raise AssertionError('Frozen watcher host exited unexpectedly')
                    time.sleep(.1)
                raise AssertionError('Timed out waiting for frozen watcher state')
            def command(value,action,**extra):
                identity=uuid.uuid4().hex
                inbox=profile/'Observer'/f"control-{child.pid}-{value['control']['id']}"
                request=dict(id=identity,control_id=value['control']['id'],session_id=value['session_id'],
                             created_at=time.time(),action=action,**extra)
                target=inbox/f'command-{identity}.json'
                temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(request),encoding='utf-8');temporary.replace(target)
                return identity
            value=wait_for(lambda s:s.get('control',{}).get('state')=='stopped')
            command(value,'start')
            value=wait_for(lambda s:bool(s.get('control',{}).get('pending')))
            command(value,'reject',candidate_id=value['control']['pending'][0]['candidate_id'])
            value=wait_for(lambda s:len(s.get('control',{}).get('suggestions',{}).get('rows',[]))==2)
            assert {row['stream'] for row in value['control']['suggestions']['rows']}=={'primary','secondary'}
            assert not any(e['reference'] in ('John 3:19','John 3:20') and e['outcome']=='COMMAND_ACCEPTED' for e in value['delivery_events'])
            assert 'SECRET-' not in json.dumps(value)
            selected=next(row for row in value['control']['suggestions']['rows'] if row['stream']=='primary')
            bad=command(value,'send_suggestion',suggestion_id=selected['id'],reference='John 3:21')
            value=wait_for(lambda s:any(row['id']==bad and row['outcome']=='rejected' for row in s['control']['results']))
            command(value,'send_suggestion',suggestion_id=selected['id'])
            value=wait_for(lambda s:any(row['id']==selected['id'] and row['state']=='accepted' for row in s['control']['suggestions']['rows']))
            row=next(row for row in value['control']['suggestions']['rows'] if row['id']==selected['id'])
            accepted=[e for e in value['delivery_events'] if e['candidate_id']==row['candidate_id'] and e['outcome']=='COMMAND_ACCEPTED']
            assert len(accepted)==1 and accepted[0]['source']=='WATCHER-MANUAL' and accepted[0]['stream']=='primary'
            duplicate=command(value,'send_suggestion',suggestion_id=selected['id'])
            value=wait_for(lambda s:any(row['id']==duplicate and row['outcome']=='failed' for row in s['control']['results']))
            command(value,'stop')
            value=wait_for(lambda s:s['control']['state']=='stopped')
            stopped=command(value,'send_suggestion',suggestion_id=selected['id'])
            value=wait_for(lambda s:any(row['id']==stopped and row['outcome']=='rejected' for row in s['control']['results']))
            child.stdin.write('{"action":"shutdown"}\n');child.stdin.flush();child.wait(timeout=30)
            assert child.returncode==0
            print(json.dumps(dict(result='PASS',native=os.name,frozen=True,watcher='actual bilingual watcher loop with fake model replies',
                candidate_id=row['candidate_id'],accepted_event=accepted[0],duplicateRejected=True,stoppedActionRejected=True,
                microphoneSTT='NOT USED - callback replay',presentation='FAKE CONTROLLER')))
        finally:
            if child and child.poll() is None:
                try:
                    child.stdin.write('{"action":"shutdown"}\n');child.stdin.flush();child.wait(timeout=30)
                except (OSError,subprocess.TimeoutExpired):child.kill();child.wait(timeout=10)
