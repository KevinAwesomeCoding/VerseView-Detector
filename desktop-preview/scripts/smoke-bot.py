"""Frozen owned bot/bridge lifecycle; only loopback HTTP and fake engine services."""
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
with tempfile.TemporaryDirectory(prefix='vv-bot-smoke-') as temporary:
    directory=Path(temporary);profile=directory/'QA/Backend';profile.mkdir(parents=True)
    settings=dict(language='English',stt_engine='deepgram',deepgram_api_key='SECRET-QA-STT',
        manual_confirm=True,verify=False,llm_enabled=False,auto_save_notes=False,
        discord_bot_token='SECRET-SYNTHETIC-TOKEN',qa_bot_silence=True,qa_bot_scenario='start-and-goto')
    (profile/'settings.json').write_text(json.dumps(settings),encoding='utf-8')
    child=None;bot_pid=None
    def alive(pid):
        if os.name=='nt':
            result=subprocess.run(['tasklist','/FI',f'PID eq {pid}','/FO','CSV','/NH'],capture_output=True,text=True)
            return f'"{pid}"' in result.stdout
        try:os.kill(pid,0);return True
        except ProcessLookupError:return False
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
                    if child.poll() is not None:raise AssertionError('Frozen bot host exited unexpectedly')
                    time.sleep(.1)
                raise AssertionError('Timed out waiting for bot state')
            def command(value,action):
                identity=uuid.uuid4().hex
                inbox=profile/'Observer'/f"control-{child.pid}-{value['control']['id']}"
                request=dict(id=identity,control_id=value['control']['id'],session_id=value['session_id'],created_at=time.time(),action=action)
                target=inbox/f'command-{identity}.json';temp=target.with_suffix('.tmp')
                temp.write_text(json.dumps(request),encoding='utf-8');temp.replace(target);return identity
            value=wait_for(lambda s:s.get('control',{}).get('state')=='stopped')
            assert value['control']['bot']['status']=='stopped' and value['control']['bot']['pid'] is None
            command(value,'start_bot')
            value=wait_for(lambda s:s['control']['bot']['status']=='online')
            assert value['control']['bot']['proof']==dict(frozen=True,guiImported=False)
            bot_pid=value['control']['bot']['pid'];assert bot_pid!=child.pid and alive(bot_pid)
            value=wait_for(lambda s:any(e['route']=='/close' and e['http_status']==200 for e in s['control']['bot']['events']))
            accepted=[e for e in value['delivery_events'] if e['outcome']=='COMMAND_ACCEPTED']
            assert [e['reference'] for e in accepted]==['John 3:19','John 3:20'],accepted
            assert all(e['source']=='DISCORD-MANUAL' and e['stream']=='unknown' for e in accepted)
            bridge_ids={e['id'] for e in value['control']['bot']['events'] if e['route'] in ('/goto','/next')}
            assert {e['candidate_id'] for e in accepted}==bridge_ids
            suppressed=[e for e in value['delivery_events'] if e['stage']=='dedup' and e['outcome']=='SUPPRESSED']
            assert len(suppressed)==2 and all(e['source']=='DISCORD-MANUAL' for e in suppressed)
            assert 'SECRET-' not in json.dumps(value)
            command(value,'stop_bot');value=wait_for(lambda s:s['control']['bot']['status']=='stopped')
            assert value['control']['state']=='running' and not alive(bot_pid)
            command(value,'stop');value=wait_for(lambda s:s['control']['state']=='stopped')
            # Restore/discard must still be chosen locally; bot Start cannot bypass recovery.
            command(value,'start_bot')
            value=wait_for(lambda s:s['control']['bot']['status']=='online')
            value=wait_for(lambda s:any(e['route']=='/start' and e['http_status']==409 for e in s['control']['bot']['events']))
            assert value['control']['state']=='stopped'
            bot_pid=value['control']['bot']['pid']
            child.stdin.close();child.wait(timeout=30);assert child.returncode==0
            assert not alive(bot_pid)
            print(json.dumps(dict(result='PASS',native=os.name,frozenBot=True,guiImported=False,
                optIn=True,accepted=accepted,privateBridgeIDsMatched=True,stopBotLeavesEngineRunning=True,
                recoveryStartRejected=True,parentEOFStopsBot=True,discord='SYNTHETIC CHILD — NO DISCORD SDK/NETWORK',
                microphoneSTT='NOT USED',presentation='FAKE CONTROLLER')))
        finally:
            if child and child.poll() is None:
                try:
                    child.stdin.write('{"action":"shutdown"}\n');child.stdin.flush();child.wait(timeout=30)
                except (OSError,ValueError,subprocess.TimeoutExpired):child.kill();child.wait(timeout=10)
