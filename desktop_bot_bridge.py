"""Private, owned adapter for the existing bot's HTTP command vocabulary.

The legacy bridge/GUI is unchanged. This instance uses an ephemeral loopback
port, a private token and expiring request identities. Engine power reuses the
desktop inbox; manual references use the existing guarded delivery boundary.
"""
from contextlib import contextmanager
import datetime as dt
import hmac
from http.server import HTTPServer
import json
import logging
import math
import os
import re
import secrets
import threading
import time
import urllib.parse
import uuid

from parse_reference_eng import BOOK_CHAPTER_COUNTS
from vv_bot_bridge import _BridgeHandler


def normalized_reference(engine,reference):
    reference=engine._normalize_delivery_reference(reference)
    if not reference or ':' not in reference:return None
    book,cv=reference.rsplit(' ',1);chapter,verse=map(int,cv.split(':'))
    bounded=reference.replace('Psalm ','Psalms ',1) if book=='Psalm' else reference
    return reference if (book in BOOK_CHAPTER_COUNTS and 1<=chapter<=BOOK_CHAPTER_COUNTS[book]
                         and verse>0 and not engine._reject_verse_out_of_range(bounded)) else None


def current_reference(engine):
    if not engine.current_book or not str(engine.current_chapter or '').isdigit() or not str(engine.current_verse or '').isdigit():
        return None
    return normalized_reference(engine,f'{engine.current_book} {engine.current_chapter}:{engine.current_verse}')


def stepped_reference(engine, delta):
    """Step from known engine context using its canonical chapter/verse bounds."""
    reference=current_reference(engine)
    if not reference:return None
    book,cv=reference.rsplit(' ',1);chapter,verse=map(int,cv.split(':'))
    books=list(BOOK_CHAPTER_COUNTS)
    if book not in BOOK_CHAPTER_COUNTS:return None
    if delta>0:
        candidate=f'{book} {chapter}:{verse+1}'
        if normalized_reference(engine,candidate):return candidate
        if chapter<BOOK_CHAPTER_COUNTS[book]:return f'{book} {chapter+1}:1'
        index=books.index(book)+1
        return f'{books[index]} 1:1' if index<len(books) else None
    if verse>1:return f'{book} {chapter}:{verse-1}'
    if chapter>1:chapter-=1
    else:
        index=books.index(book)-1
        if index<0:return None
        book=books[index];chapter=BOOK_CHAPTER_COUNTS[book]
    for number in range(2,202):
        if not normalized_reference(engine,f'{book} {chapter}:{number}'):
            return f'{book} {chapter}:{number-1}'
    return None


class ManagedBotBridge:
    def __init__(self,runtime,clock=time.time):
        self.runtime,self.clock=runtime,clock
        self.token=secrets.token_urlsafe(32)
        self.server=self.thread=None
        self.lock=threading.Condition(threading.RLock())
        self.seen={};self.events=[];self.inflight=0;self.closing=False

    def start(self):
        handler=type('OwnedVerseViewBridge',(_ManagedHandler,),{'bridge':self})
        self.server=HTTPServer(('127.0.0.1',0),handler)
        self.thread=threading.Thread(target=self.server.serve_forever,name='VerseViewBotBridge',daemon=True)
        self.thread.start()

    @property
    def port(self):return self.server.server_address[1]

    def authenticate(self,headers):
        if not hmac.compare_digest(headers.get('X-VerseView-Token',''),self.token):return None
        identity=headers.get('X-VerseView-Request','')
        try:created=float(headers.get('X-VerseView-Created',''))
        except (TypeError,ValueError):return None
        if not re.fullmatch(r'[a-f0-9]{32}',identity) or not math.isfinite(created) or not 0<=self.clock()-created<=10:return None
        with self.lock:
            self.seen={key:value for key,value in self.seen.items() if self.clock()-value<=10}
            if self.closing or identity in self.seen or len(self.seen)>=4096:return None
            self.seen[identity]=created
        return identity

    @contextmanager
    def delivery(self):
        with self.lock:
            if self.closing or self.runtime.state()!='running' or self.runtime.stop_requested.is_set():
                raise ValueError('Engine is not ready for remote delivery')
            self.inflight+=1
        try:yield
        finally:
            with self.lock:self.inflight-=1;self.lock.notify_all()

    def power(self,action,identity):
        snapshot=self.runtime.publisher.snapshot() or {};control=snapshot.get('control') or {}
        if action not in control.get('actions',[]):return False
        directory=self.runtime.publisher.directory/f"control-{os.getpid()}-{control['id']}"
        request=dict(id=identity,control_id=control['id'],session_id=snapshot['session_id'],created_at=self.clock(),action=action)
        temporary=directory/f'.bot-command-{identity}.tmp'
        try:
            with open(temporary,'x',encoding='utf-8',opener=lambda name,flags:os.open(name,flags,0o600)) as handle:
                json.dump(request,handle)
            os.replace(temporary,directory/f'command-{identity}.json')
        finally:temporary.unlink(missing_ok=True)
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            result=next((row for row in (self.runtime.publisher.snapshot() or {}).get('control',{}).get('results',[]) if row['id']==identity),None)
            if result:return result['outcome']=='requested'
            if self.closing:return False
            time.sleep(.03)
        return False

    def present(self,reference,identity):
        engine=self.runtime.engine
        normalized=normalized_reference(engine,reference)
        if not normalized:return False
        accepted=engine.deliver_verse(normalized,getattr(engine,'_controller',None),bypass_cooldown=True,
            confidence=1.0,source='DISCORD-MANUAL',stream='unknown',candidate_id=identity)
        if accepted and normalized and not self.runtime.stop_requested.is_set():
            try:
                book,cv=normalized.rsplit(' ',1);chapter,_,verse=cv.partition(':')
                engine.set_context(book,chapter,verse)
                engine.add_to_verse_history(normalized,source='DISCORD-MANUAL')
            except Exception:logging.getLogger(__name__).exception('Accepted bot command context update failed')
        return accepted

    def record(self,identity,route,code):
        with self.lock:
            self.events=(self.events+[dict(id=identity,route=route,http_status=code,
                timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),outcome='acknowledged' if code==200 else 'rejected')])[-32:]

    def snapshot(self):
        with self.lock:return [dict(row) for row in self.events]

    def drain(self):
        with self.lock:self.lock.wait_for(lambda:self.inflight==0)

    def stop(self):
        with self.lock:self.closing=True
        if self.server:
            self.server.shutdown();self.server.server_close()
        if self.thread:self.thread.join(timeout=2)


class _ManagedHandler(_BridgeHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(3)

    def do_GET(self):
        self.request_id=self.bridge.authenticate(self.headers)
        self.route=urllib.parse.urlsplit(self.path).path.rstrip('/')
        if not self.request_id:self._send(403,'Rejected');return
        try:
            if len(self.path)>1024:self._send(400,'Invalid request');return
            if self.route in ('/start','/stop'):
                ok=self.bridge.power(self.route[1:],self.request_id)
                self._send(200 if ok else 409,'Engine request acknowledged; use /status to check readiness.');return
            if self.route=='/status':
                self._send(200,'Engine '+self.bridge.runtime.state());return
            if self.route=='/version':return self._handle_version({})
            with self.bridge.delivery():
                if self.route in ('/goto','/present','/next','/prev'):
                    engine=self.bridge.runtime.engine
                    params=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    reference=(params.get('ref') or [''])[0] if self.route=='/goto' else (
                        current_reference(engine) if self.route=='/present' else stepped_reference(engine,1 if self.route=='/next' else -1))
                    if not reference or len(reference)>128:self._send(409,'Explicit verse required');return
                    ok=self.bridge.present(reference,self.request_id)
                    self._send(200 if ok else 409,'Verse command accepted; verify the visible output.');return
                if self.route=='/clear':return self._handle_clear({})
                if self.route=='/close':return self._handle_close({})
                self._send(404,'Unknown action')
        except Exception:
            logging.getLogger(__name__).exception('Owned bot bridge request failed')
            self._send(503,'Control unavailable')

    def _send(self,code,body):
        if code>=400:
            body={403:'Bridge request rejected.',409:'Action was not accepted. Check the local dashboard and delivery activity.',
                  503:'Engine control is unavailable.'}.get(code,'Control request failed. Inspect the private backend log.')
        if getattr(self,'request_id',None):self.bridge.record(self.request_id,self.route,code)
        super()._send(code,body)
