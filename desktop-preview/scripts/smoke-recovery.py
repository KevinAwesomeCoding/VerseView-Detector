"""Native frozen-engine recovery regression; fake speech/browser, no GUI/audio."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

root = Path(__file__).resolve().parents[1]
backend = Path((root/'backend-build/latest.txt').read_text(encoding='utf-8').strip())
executable = backend / ('VerseViewBackend.exe' if os.name == 'nt' else 'VerseViewBackend')
with tempfile.TemporaryDirectory(prefix='vv-recovery-smoke-') as temporary:
    directory = Path(temporary)
    profile = directory/'QA'/'Backend'; profile.mkdir(parents=True)
    (profile/'settings.json').write_text(json.dumps({'language':'English','stt_engine':'deepgram',
        'deepgram_api_key':'QA-KEY','sarvam_api_key':'QA-KEY','dual_stt_enabled':True,
        'secondary_language':'ml','secondary_stt_engine':'sarvam','manual_confirm':True,
        'verify':False,'llm_enabled':False,'auto_save_notes':False,'auto_start':True}), encoding='utf-8')
    child = None
    handles = []
    def wait_for(read, predicate, timeout=30):
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            try:
                value=read()
                if predicate(value): return value
            except (OSError, ValueError, KeyError, TypeError): pass
            if child.poll() is not None: raise AssertionError('Frozen recovery host exited unexpectedly')
            time.sleep(.1)
        raise AssertionError('Timed out waiting for frozen recovery state')
    def launch():
        global child
        log_path=directory/(uuid.uuid4().hex+'.log')
        handle=log_path.open('wb');handles.append(handle)
        child=subprocess.Popen([str(executable),'--profile',str(profile),'--verify-isolated'],
            stdin=subprocess.PIPE,stdout=handle,stderr=handle,text=True,
            env={**os.environ,'VV_PREVIEW_TEST_PROFILE':'1'})
        def ready():
            for line in log_path.read_text(encoding='utf-8',errors='replace').splitlines():
                try:
                    value=json.loads(line)
                    if value.get('ready'):return value
                except ValueError:pass
            return {}
        value=wait_for(ready,lambda value:value.get('ready'))
        assert value['frozen'] and not value['guiImported'] and value['verification']
        return wait_for(snapshot,lambda value:value.get('control',{}).get('state')=='stopped')
    def snapshot():
        return json.loads((profile/'Observer'/f'engine-{child.pid}.json').read_bytes())
    def command(value, action, **extra):
        identity=uuid.uuid4().hex
        inbox=profile/'Observer'/f"control-{child.pid}-{value['control']['id']}"
        request={'id':identity,'control_id':value['control']['id'],'session_id':value['session_id'],
                 'created_at':time.time(),'action':action,**extra}
        target=inbox/f'command-{identity}.json'
        temp=target.with_suffix('.tmp');temp.write_text(json.dumps(request),encoding='utf-8');temp.replace(target)
        return identity
    checkpoint=profile/'Recovery/session.json'
    try:
        value=launch()
        assert not checkpoint.exists(), 'Idle launch must not create or overwrite a checkpoint'
        command(value,'start')
        saved=wait_for(lambda:json.loads(checkpoint.read_bytes()),lambda value:value.get('reason')=='autosave',timeout=30)
        assert saved['data']['current_chapter']=='3'
        assert saved['data']['current_verse']=='17'
        assert 'John 3:17' in saved['data']['transcript']
        assert 'John 3:16' in saved['data']['transcript_secondary']
        assert 'യോഹന്നാൻ' in saved['data']['raw_preview']['secondary']
        assert 'QA-KEY' not in json.dumps(saved)
        for key in ('settings','stt_log','pending','queue','discord_msg_id'):assert key not in saved['data']
        child.kill();child.wait(timeout=10)
        value=launch()
        assert value['control']['recovery']['status']=='available'
        assert 'start' not in value['control']['actions']
        assert not value['delivery_events'] and not value['control']['pending']
        command(value,'restore_session',recovery_revision=value['control']['recovery']['revision'])
        value=wait_for(snapshot,lambda value:value.get('control',{}).get('recovery',{}).get('status')=='staged')
        assert value['control']['state']=='stopped'
        assert not value['delivery_events'] and not value['transcripts']
        child.stdin.write('{"action":"shutdown"}\n');child.stdin.flush();child.wait(timeout=30)
        assert child.returncode==0
        assert checkpoint.exists(), 'Restore before Start must retain the original checkpoint'
        print(json.dumps({'result':'PASS','native':os.name,'frozen':True,'autosaveIntervalSeconds':15,
            'engineStringContext':True,'crashCheckpointRetained':True,'restoreOnlyRemainsStopped':True,
            'microphoneSTT':'NOT USED - callback replay','presentation':'FAKE CONTROLLER'}))
    finally:
        if child and child.poll() is None:
            try:
                child.stdin.write('{"action":"shutdown"}\n');child.stdin.flush();child.wait(timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                child.kill();child.wait(timeout=10)
        for handle in handles:handle.close()
