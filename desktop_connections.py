"""Owned, revision-bound file transfers and bounded integration/model actions."""
import copy
import hashlib
import ipaddress
import json
import logging
from pathlib import Path
import threading
import time
import uuid
import desktop_options
from desktop_sessions import read_private
from desktop_notes import write_text, stamp


class ConnectionError(ValueError): pass


class Connections:
    def __init__(self, runtime, store, settings):
        self.runtime,self.store,self.settings=runtime,store,settings
        self.lock=threading.RLock();self.worker=None;self.cancelled=threading.Event()
        self.value=dict(status='idle',message='',operation='',endpoint='',model='',role='',completed_at=None)
        self.export=None;self.review=None;self.discovered=''

    @property
    def busy(self): return bool(self.worker and self.worker.is_alive())

    def target(self,raw,role):
        selected='verse' if role=='watcher' else role
        default=desktop_options.settings.get_recommended_local_model(selected)
        model=(raw.get('local_llm_model') or raw.get('local_llm_model_verse') or default) if role=='watcher' else (raw.get('local_llm_model_'+role) or raw.get('local_llm_model') or default)
        endpoint=desktop_options.resolved_endpoint(raw)
        return dict(endpoint=endpoint if desktop_options.endpoint(endpoint,False) else '',model=model if desktop_options.valid('local_llm_model',model) else '',keep_alive=raw.get('local_llm_keep_alive_'+selected,'5m'))

    def snapshot(self):
        with self.lock:
            try:raw,_=self.store.load()
            except (ValueError,OSError):raw={}
            return dict(**self.value,busy=self.busy,export=copy.deepcopy(self.export),atem_review=copy.deepcopy(self.review),discovered=self.discovered,
                        local_targets={role:self.target(raw,role) for role in ('verse','outline','summary','watcher')},
                        gcp_configured=bool(self.store.config.resolve_gcp_credentials_path(raw)),
                        credentials={k:bool(raw.get(k)) for k in desktop_options.SECRETS})

    def checked(self, revision, stopped=True):
        self.settings.refresh();current=self.settings.snapshot()
        if not current or revision!=current['revision']: raise ConnectionError('Settings changed. Reload before continuing.')
        if getattr(self.store,'blocked',lambda:False)():raise ConnectionError('Wait for settings sync or connection work.')
        if self.busy or (stopped and self.runtime.state()!='stopped'): raise ConnectionError('Stop listening and wait for the current connection action.')
        if self.runtime.notes.busy or self.runtime.notes.pending_auto: raise ConnectionError('Wait for notes to finish.')
        if getattr(self.runtime.warmup,'thread',None) and self.runtime.warmup.thread.is_alive(): raise ConnectionError('Wait for startup model warmup to finish.')
        if self.runtime.bot.snapshot()['status'] not in ('stopped','failed'): raise ConnectionError('Stop the remote bot before changing connections.')
        return self.store.load()

    def run(self, operation, revision, role='verse', review=None, isolated=False):
        raw,_=self.checked(revision)
        if operation not in ('local_test','local_warm','atem_discover','atem_on','atem_off'): raise ConnectionError('Unsupported connection action.')
        if role not in ('verse','outline','summary','watcher'): raise ConnectionError('Choose a supported model role.')
        target_config=self.target(raw,role);endpoint=target_config['endpoint'];model=target_config['model']
        if operation.startswith('local') and (not desktop_options.endpoint(endpoint,False) or not model): raise ConnectionError('Save a valid local endpoint and model first.')
        target=raw.get('atem_ip','')
        if operation in ('atem_on','atem_off'):
            if isolated is not True or not self.review or review!=self.review['id'] or self.review['settings_revision']!=revision or time.monotonic()>self.review['expires'] or self.review['target']!=target: raise ConnectionError('Review the exact isolated ATEM target before sending a command.')
            self.review=None
        with self.lock:
            cancel=self.cancelled=threading.Event()
            self.value=dict(status='running',message='Action in progress. Stop and emergency controls remain available.',operation=operation,endpoint=endpoint if operation.startswith('local') else target,model=model if operation.startswith('local') else '',role=role,completed_at=None)
        def work():
            try:
                if self.runtime.verification:
                    time.sleep(1.5);ok=not raw.get('qa_connection_failure');message='Synthetic connection result; no network or hardware contacted.'
                    if operation=='atem_discover': self.discovered='192.0.2.10'
                elif operation.startswith('local'):
                    args=dict(endpoint=endpoint,model=model,timeout=raw.get('local_llm_timeout',45),auth_token=raw.get('local_llm_auth_token',''),extra_headers=raw.get('local_llm_extra_headers',''))
                    if operation=='local_warm':args.update(role=role,keep_alive=target_config['keep_alive'])
                    ok,_private=(self.runtime.engine.warm_local_llm_model if operation=='local_warm' else self.runtime.engine.test_local_llm_connection)(**args)
                    message='Local model '+('warmup' if operation=='local_warm' else 'connection test')+(' succeeded.' if ok else ' failed. Check the endpoint, installed model and authentication; no retry was made.')
                elif operation=='atem_discover':
                    found=self.runtime.engine._discover_atem_ip();self.discovered=str(ipaddress.IPv4Address(found)) if found else '';ok=bool(found);message='Discovered '+self.discovered+'. Enter this address and save before reviewing a keyer command.' if found else 'No ATEM discovered. Enter its known address or check the network.'
                else:
                    import PyATEMMax
                    sw=PyATEMMax.ATEMMax()
                    try:
                        sw.connect(target)
                        if not sw.waitForConnection(infinite=False,timeout=5):raise ConnectionError('ATEM connection timed out.')
                        sw.setKeyerOnAirEnabled(0,0,operation=='atem_on');time.sleep(.3)
                        ok=True;message='Keyer '+('On' if operation=='atem_on' else 'Off')+' command requested. Actual switcher/output state is unverified.'
                    finally:sw.disconnect()
                with self.lock:
                    if cancel.is_set():return
                    self.value.update(status='complete' if ok else 'failed',message=message,completed_at=stamp())
            except Exception:
                logging.getLogger(__name__).exception('Connection action failed')
                with self.lock:
                    if not cancel.is_set():self.value.update(status='failed',message='Connection action failed; output state is unknown. Check setup before another explicit action. No retry was made.',completed_at=stamp())
        self.worker=threading.Thread(target=work,name='DesktopConnections',daemon=True);self.worker.start()

    def cancel(self):
        # No cancelling ATEM commands mid-flight: they may already have changed hardware.
        if self.value['operation'] in ('atem_on','atem_off') and self.busy: raise ConnectionError('Wait for the bounded ATEM request; then inspect output before sending Off.')
        self.cancelled.set();self.value.update(status='cancelled',message='Cancelled. In-flight I/O may finish; late results are ignored. No retry was made.')

    def prepare_atem(self, revision):
        raw,_=self.checked(revision);target=raw.get('atem_ip','')
        if not target or not desktop_options.valid('atem_ip',target):raise ConnectionError('Discover or enter and save the exact ATEM address first.')
        self.review=dict(id=uuid.uuid4().hex,target=target,settings_revision=revision,expires=time.monotonic()+30,
                         message='Only approve if this exact switcher is isolated from audiences, projectors, broadcasts and livestreams. Keyer 1 on Mix Effect 1 will change. Command acceptance does not verify visible output.')

    def prepare_export(self, revision, include_credentials):
        raw,_=self.checked(revision)
        if type(include_credentials) is not bool:raise ConnectionError('Choose whether credentials are included.')
        from desktop_settings import project
        payload=dict(schema=1,kind='verseview-settings',values=project(raw))
        if include_credentials:
            from desktop_cloud_settings import CREDENTIALS
            payload['credentials']={k:raw.get(k,'') for k in set(CREDENTIALS)|set(desktop_options.SECRETS)}
            path=self.store.config.resolve_gcp_credentials_path(raw)
            if path:payload['gcp_credentials']=read_private(Path(path)).decode('utf-8')
        identity=uuid.uuid4().hex;target=Path(self.runtime.profile)/'Exports'/(identity+'.txt')
        sha=write_text(target,json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
        self.export=dict(id=identity,source_id=revision,kind='profile',name='VerseView-settings.json',sha256=sha,include_credentials=include_credentials)
        self.value.update(status='complete',message='Settings export prepared '+('including credentials.' if include_credentials else 'without credentials.'))

    def import_file(self, revision, attachment_id, include_credentials):
        raw,storage_revision=self.checked(revision)
        if not isinstance(attachment_id,str) or len(attachment_id)!=32 or any(c not in '0123456789abcdef' for c in attachment_id) or type(include_credentials) is not bool:raise ConnectionError('Invalid import request.')
        path=Path(self.runtime.profile)/'Imports'/(attachment_id+'.json')
        try:
            packet=json.loads(read_private(path));kind=packet.get('kind');text=packet.get('text')
            if kind=='gcp':
                if not include_credentials or not isinstance(text,str) or not self.store.config.validate_service_account_text(text):raise ConnectionError('Choose a valid Google service-account JSON.')
                changes={};credential=text
            elif kind=='settings':
                payload=json.loads(text)
                if not isinstance(payload,dict) or payload.get('schema')!=1 or payload.get('kind')!='verseview-settings' or not set(payload)<=set(('schema','kind','values','credentials','gcp_credentials')):raise ConnectionError('Choose an exported VerseView settings file.')
                from desktop_settings import validate_changes,project
                changes=validate_changes(payload.get('values'),project(raw),self.settings.raw['devices'])
                credential=None
                if include_credentials:
                    from desktop_cloud_settings import CREDENTIALS,validate_cloud
                    secrets=payload.get('credentials',{})
                    if not isinstance(secrets,dict) or not set(secrets)<=set(CREDENTIALS)|set(desktop_options.SECRETS):raise ConnectionError('Unsupported imported credential.')
                    changes.update(desktop_options.validate_secrets({k:v for k,v in secrets.items() if k in desktop_options.SECRETS and v}))
                    basic={k:v for k,v in secrets.items() if k in CREDENTIALS and v}
                    if basic:changes.update({k:v for k,v in validate_cloud({'credentials':basic},raw).items() if k in basic})
                    credential=payload.get('gcp_credentials')
                    if credential is not None and (not isinstance(credential,str) or not self.store.config.validate_service_account_text(credential)):raise ConnectionError('Imported Google credential is invalid.')
            else:raise ConnectionError('Unsupported import type.')
            # Same atomic store transaction as credential sync, with an explicit validated field allowlist.
            self.store.apply_import(changes,credential,storage_revision)
            self.settings.refresh();self.runtime.has_started=False
            self.value.update(status='complete',message='Import saved. Existing sessions and unrelated settings were retained. Applies on the next Start.',completed_at=stamp())
        except (ConnectionError,ValueError,TypeError,KeyError):raise ConnectionError('Import was not applied. Check file format, credential scope and settings values.') from None
        finally:path.unlink(missing_ok=True)
