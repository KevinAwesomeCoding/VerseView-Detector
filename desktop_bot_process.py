"""Owned bot subprocess transport and parent-pipe lifetime (no Discord import)."""
import asyncio
import json
import os
from pathlib import Path
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


def emit(event, **values):
    if os.getenv('VV_MANAGED_BOT') == '1':
        print(json.dumps(dict(bot_event=event, **values)), flush=True)


def bridge_request(base, endpoint, params=None, timeout=8):
    url=base+endpoint+('?' + urllib.parse.urlencode(params) if params else '')
    headers={}
    if os.getenv('VV_BRIDGE_TOKEN'):
        headers={'X-VerseView-Token':os.environ['VV_BRIDGE_TOKEN'],
                 'X-VerseView-Request':uuid.uuid4().hex,'X-VerseView-Created':str(time.time())}
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=timeout) as response:
            return response.status,response.read(8192).decode('utf-8',errors='replace')
    except urllib.error.HTTPError as error:
        return error.code,error.read(8192).decode('utf-8',errors='replace')
    except Exception:
        return 0,'Local bridge unavailable.'


async def owned_lifetime(run):
    """Cancel and close the SDK on shutdown/EOF, including during reconnect sleep."""
    loop=asyncio.get_running_loop();shutdown=asyncio.Event()
    def parent():
        try:
            for line in sys.stdin:
                try:
                    if json.loads(line)=={'action':'shutdown'}:break
                except ValueError:pass
        finally:
            try:loop.call_soon_threadsafe(shutdown.set)
            except RuntimeError:pass
    threading.Thread(target=parent,name='BotParent',daemon=True).start()
    task=asyncio.create_task(run());ending=asyncio.create_task(shutdown.wait())
    try:
        await asyncio.wait([task,ending],return_when=asyncio.FIRST_COMPLETED)
    finally:
        task.cancel();ending.cancel()
        await asyncio.gather(task,ending,return_exceptions=True)


def verification_main():
    """Explicit QA only: real owned process/private HTTP, no Discord SDK/network."""
    if (os.getenv('VV_MANAGED_BOT')!='1' or os.getenv('VV_PREVIEW_TEST_PROFILE')!='1'
            or 'QA' not in Path(os.getenv('VERSEVIEW_PROFILE_DIRECTORY','')).parts):
        raise SystemExit('Bot verification requires an explicit private QA profile')
    base='http://127.0.0.1:'+os.environ['VV_PORT']
    code,_=bridge_request(base,'/status')
    if code!=200:raise SystemExit('Synthetic bridge check failed')
    emit('ready',verification=True,frozen=bool(getattr(sys,'frozen',False)),
         guiImported='tkinter' in sys.modules or 'vv_gui' in sys.modules)
    if os.getenv('VV_BOT_QA_SCENARIO')=='start-and-goto':
        code,_=bridge_request(base,'/start');emit('qa',route='/start',code=code)
        if code==200:
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                if bridge_request(base,'/status')[1]=='Engine running':break
                time.sleep(.1)
            else:raise SystemExit('Synthetic engine did not start')
            for route,params,expected in [('/goto',{'ref':'John 3:19'},200),('/next',None,200),('/prev',None,409),('/present',None,409),('/version',None,200),('/clear',None,200),('/close',None,200)]:
                code,_=bridge_request(base,route,params);emit('qa',route=route,code=code)
                if code!=expected:raise SystemExit('Synthetic route failed')
    for line in sys.stdin:
        try:
            if json.loads(line)=={'action':'shutdown'}:break
        except ValueError:pass

