"""Explicit, owned Discord bot lifecycle for the standalone backend."""
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import subprocess
import sys
import threading

from desktop_bot_bridge import ManagedBotBridge
import desktop_bot_process  # Frozen analysis must include the bundled script's helper.


class BotError(ValueError):
    pass


class DesktopBot:
    def __init__(self, runtime, load):
        self.runtime,self.load=runtime,load
        self.lock=threading.RLock()
        self.thread=self.child=self.bridge=None
        self.stopping=threading.Event()
        self.status='stopped';self.message='Bot is stopped. Start it explicitly to connect Discord.'
        self.proof=None;self.closed=False
        self.logger=logging.getLogger('desktop.bot.'+str(id(self)))
        self.logger.setLevel(logging.INFO);self.logger.propagate=False
        directory=Path(runtime.profile)/'Logs';directory.mkdir(mode=0o700,parents=True,exist_ok=True)
        handler=RotatingFileHandler(directory/'discord-bot.log',maxBytes=2*1024*1024,backupCount=2,encoding='utf-8')
        if os.name!='nt':os.chmod(handler.baseFilename,0o600)
        self.logger.addHandler(handler)

    def snapshot(self):
        values,_=self.load()
        with self.lock:
            value=dict(status=self.status,message=self.message,configured=bool(str(values.get('discord_bot_token') or '').strip()),
                       pid=self.child.pid if self.child and self.child.poll() is None else None,
                       verification=self.runtime.verification,proof=self.proof)
            bridge=self.bridge
        value['events']=bridge.snapshot() if bridge else []
        return value

    def start(self):
        values,_=self.load()
        token=str(values.get('discord_bot_token') or '').strip()
        guild=str(values.get('vv_guild_id') or '').strip()
        if not token:raise BotError('Discord credentials are missing. Configure the private backend settings file.')
        if len(token)>512 or any(ord(char)<33 for char in token):raise BotError('Discord token configuration is invalid.')
        if guild and (not re.fullmatch(r'[0-9]{1,20}',guild) or not 0<int(guild)<2**64):
            raise BotError('Discord server ID configuration is invalid.')
        with self.lock:
            if self.closed or self.thread and self.thread.is_alive():raise BotError('Bot is already active or stopping.')
            self.stopping.clear();self.proof=None
            self.status='starting';self.message='Connecting the owned bot; recognition is unchanged.'
            self.thread=threading.Thread(target=self._run,args=(token,guild,values),name='VerseViewBot',daemon=True)
            self.thread.start()

    def _run(self,token,guild,values):
        bridge=ManagedBotBridge(self.runtime);child=None
        try:
            bridge.start()
            with self.lock:self.bridge=bridge
            env={**os.environ,'VV_RUN_BOT':'1','VV_MANAGED_BOT':'1','VV_BOT_TOKEN':token,'VV_GUILD_ID':guild,
                 'VV_HOST':'127.0.0.1','VV_PORT':str(bridge.port),'VV_BRIDGE_TOKEN':bridge.token,
                 'VERSEVIEW_PROFILE_DIRECTORY':str(self.runtime.profile),'PYTHONUNBUFFERED':'1'}
            # Never inherit verification switches into a normal bot.
            for key in ('VV_BOT_VERIFY','VV_BOT_QA_SCENARIO'):env.pop(key,None)
            if self.runtime.verification:
                env.update(VV_BOT_VERIFY='1',VV_PREVIEW_TEST_PROFILE='1',
                           VV_BOT_QA_SCENARIO='start-and-goto' if values.get('qa_bot_scenario')=='start-and-goto' else 'idle')
            command=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,str(Path(__file__).with_name('desktop_backend.py'))]
            with self.lock:
                if self.stopping.is_set():return
                child=subprocess.Popen(command,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                    text=True,encoding='utf-8',errors='replace',bufsize=1,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                self.child=child
            for line in child.stdout:
                self.logger.info('%s',line.rstrip()[:8192])
                try:event=json.loads(line)
                except ValueError:continue
                if not isinstance(event,dict):continue
                with self.lock:
                    if self.stopping.is_set():continue
                    if event.get('bot_event')=='ready' and event.get('verification') is self.runtime.verification:
                        if event.get('guiImported') is not False or event.get('frozen') is not bool(getattr(sys,'frozen',False)):
                            raise BotError('Owned bot runtime did not match its parent')
                        self.status='online';self.message='Synthetic bot online — no Discord connection.' if self.runtime.verification else 'Discord bot online. Commands use the owned backend.'
                        self.proof=dict(frozen=event.get('frozen') is True,guiImported=event.get('guiImported') is True)
                    elif event.get('bot_event')=='error':
                        self.status='failed';self.message='Discord authentication failed. Check the private credentials; no retry was scheduled.'
            child.wait()
            with self.lock:
                if not self.stopping.is_set() and self.status!='failed':
                    self.status='failed';self.message='Owned bot exited. Inspect the private bot log before restarting.'
        except Exception:
            self.logger.exception('Owned bot failed')
            with self.lock:
                self.status='failed';self.message='Bot could not start. Inspect the private bot log.'
        finally:
            if child and child.poll() is None:self._end_child(child)
            if child:
                for pipe in (child.stdin,child.stdout):
                    if pipe and not pipe.closed:pipe.close()
            bridge.stop()
            with self.lock:
                self.child=None
                if self.stopping.is_set():
                    self.status='stopped';self.message='Bot stopped. Recognition is unchanged.'

    @staticmethod
    def _end_child(child):
        try:
            child.stdin.write('{"action":"shutdown"}\n');child.stdin.flush();child.stdin.close()
        except (OSError,ValueError):pass
        try:child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.terminate()
            try:child.wait(timeout=2)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=2)

    def stop(self):
        with self.lock:
            if not self.thread or not self.thread.is_alive():return
            self.stopping.set();self.status='stopping';self.message='Stopping the owned Discord bot.'
            child=self.child
        if child:
            threading.Thread(target=self._end_child,args=(child,),name='BotShutdown',daemon=True).start()

    def drain_delivery(self):
        with self.lock:bridge=self.bridge
        if bridge:bridge.drain()

    def close(self):
        self.closed=True;self.stop()
        if self.thread:self.thread.join(timeout=12)
        if self.thread and self.thread.is_alive():return False
        for handler in self.logger.handlers[:]:handler.close();self.logger.removeHandler(handler)
        return True
