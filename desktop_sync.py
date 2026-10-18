"""Credential-only private-profile sync, with a staged main-thread commit."""
import base64
import datetime as dt
import json
import logging
import re
import threading
from urllib.parse import urlsplit

MAX_BYTES=1024*1024


class SyncError(ValueError):
    pass


class SyncConflict(SyncError):
    pass


def valid_sync_url(url):
    if not isinstance(url,str) or not 1<=len(url)<=4096 or re.search(r'[\s\x00-\x1f\x7f]',url):return False
    try:
        parsed=urlsplit(url)
        return parsed.scheme in ('https','http') and bool(parsed.hostname) and not parsed.fragment and (parsed.port is None or 1<=parsed.port<=65535)
    except ValueError:return False


def download_json(url,cancelled=lambda:False):
    """Existing requests/certifi transport and timeout, with bounded content."""
    if not valid_sync_url(url):raise SyncError('Configured sync URL is invalid.')
    if cancelled():raise SyncError('Sync cancelled.')
    import requests,certifi
    with requests.get(url,timeout=10,verify=certifi.where(),stream=True) as response:
        response.raise_for_status()
        content=bytearray()
        for chunk in response.iter_content(chunk_size=8192):
            if cancelled():raise SyncError('Sync cancelled.')
            content.extend(chunk)
            if len(content)>MAX_BYTES:raise SyncError('Downloaded settings exceed the size limit.')
    return json.loads(content.decode('utf-8-sig'))


def collect(remote,config,fetch,cancelled):
    if not isinstance(remote,dict):raise SyncError('Downloaded settings are not a JSON object.')
    changes={}
    for key in config.SYNC_ALLOWED_KEYS:
        if key in remote:
            value=remote[key]
            if not isinstance(value,str) or len(value)>16384 or '\0' in value:raise SyncError('Downloaded credential values are invalid.')
            changes[key]=value
    def credential(value):
        if not config.validate_gcp_service_account_json(value) or any(not isinstance(value[key],str) for key in config._GCP_SA_REQUIRED_KEYS):
            raise SyncError('Downloaded Google credentials are invalid.')
        text=json.dumps(value,sort_keys=True,ensure_ascii=True,indent=2)
        if len(text.encode('utf-8'))>MAX_BYTES:raise SyncError('Downloaded Google credentials exceed the size limit.')
        return text
    if remote.get('type')=='service_account':return changes,credential(remote)
    payload,url=remote.get(config.GCP_CREDENTIALS_PAYLOAD_KEY),remote.get(config.GCP_CREDENTIALS_URL_KEY)
    if payload:
        try:
            if not isinstance(payload,str) or len(payload)>MAX_BYTES:raise ValueError('Invalid portable payload')
            return changes,credential(json.loads(base64.b64decode(payload,validate=True).decode('utf-8')))
        except (ValueError,TypeError,UnicodeError):
            if not url:raise SyncError('Downloaded Google credentials are invalid.') from None
    if url:
        if not valid_sync_url(url):raise SyncError('Downloaded Google credential URL is invalid.')
        if cancelled():raise SyncError('Sync cancelled.')
        return changes,credential(fetch(url,cancelled))
    return changes,None


class SettingsSync:
    def __init__(self,config,load,apply,ready,fetch=download_json):
        self.config,self.load,self.apply,self.ready,self.fetch=config,load,apply,ready,fetch
        self.lock=threading.RLock();self.cancelled=threading.Event();self.thread=None
        self.status='idle';self.message='No settings pull has run in this host.';self.updated=0;self.completed_at=None
        self.result=None;self.closed=False

    @property
    def busy(self):
        with self.lock:return self.status=='pulling'

    def snapshot(self):
        try:values,_=self.load();configured=bool(values.get('settings_sync_url'))
        except Exception:configured=False
        with self.lock:return dict(status=self.status,message=self.message,configured=configured,busy=self.status=='pulling',
                                   updated_count=self.updated,completed_at=self.completed_at)

    def auto_start(self):
        try:
            values,_=self.load()
            if values.get('settings_sync_url'):self.start()
        except Exception:
            with self.lock:self.status='failed';self.message='Startup settings sync could not begin. Check the private settings file.'

    def start(self):
        with self.lock:
            if self.closed or self.busy:raise SyncError('Settings sync is already running or closing.')
            if not self.ready():raise SyncError('Stop recognition and the bot before pulling credentials.')
            values,revision=self.load();url=values.get('settings_sync_url')
            if not valid_sync_url(url):raise SyncError('Configure a valid sync URL in the private backend settings file.')
            self.status='pulling';self.message='Pulling credentials; recognition remains stopped.';self.updated=0;self.result=None
            self.thread=threading.Thread(target=self._download,args=(url,revision),name='VerseViewSettingsSync',daemon=True)
            self.thread.start()

    def _download(self,url,revision):
        try:
            remote=self.fetch(url,self.cancelled.is_set)
            changes,credential=collect(remote,self.config,self.fetch,self.cancelled.is_set)
            result=(changes,credential,revision)
        except Exception:
            if not self.cancelled.is_set():logging.getLogger(__name__).exception('Private settings sync download or validation failed')
            result=False
        with self.lock:
            if not self.closed:self.result=result

    def tick(self):
        with self.lock:
            if self.closed or self.result is None:return
            result=self.result;self.result=None
        status,message,count='failed','Settings sync failed. Previous settings and credentials were retained; inspect the private log.',0
        if result is not False:
            try:
                if not self.ready():raise SyncConflict('Engine or bot state changed.')
                count=self.apply(*result)
                status='applied' if count else 'unchanged'
                message=f'Settings synced: {count} credential field(s) updated. They apply on the next start.' if count else 'Settings sync is already up to date.'
            except SyncConflict:
                status,message='conflict','Settings or engine/bot state changed during the pull. Nothing was applied. Review the private settings, then pull again.'
            except Exception:logging.getLogger(__name__).exception('Private settings sync commit failed')
        with self.lock:
            self.status,self.message,self.updated=status,message,count
            self.completed_at=dt.datetime.now(dt.timezone.utc).isoformat()

    def close(self):
        with self.lock:self.closed=True;self.cancelled.set();self.result=None
        if self.thread:self.thread.join(timeout=12)
        return not self.thread or not self.thread.is_alive()
