(() => {
  'use strict';
  const root=document.getElementById('verseview-prototype');
  const languages={en:'English',ml:'Malayalam',hi:'Hindi',multi:'Multilingual'};
  const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let dialog=null,opener=null,pending=null,notice='',signature='',pinned=false;
  const refresh=()=>root.dispatchEvent(new Event('preview:observer'));
  const get=()=>window.previewShell.getObserver();
  const ready=(s,action)=>s.connection==='connected'&&s.session?.control?.actions.includes(action);
  function render(s){
    const op=s.session?.control?.operator;
    if(!op)return '';
    const message=notice||op.message||(op.worship?'Worship is on. Speech continues; new verses are not sent to VerseVIEW.':'');
    return message?`<p class="vv-caption vv-operator-notice" role="status">${escape(message)}</p>`:'';
  }
  function header(s){
    const op=s.session?.control?.operator;
    return `<button class="vv-btn" type="button" data-operator="worship" aria-pressed="${op?.worship===true}" ${op&&ready(s,'set_worship')&&!pending?'':'disabled'}>Worship ${op?.worship?'on':'off'}</button><button class="vv-btn" type="button" data-operator="pin" aria-pressed="${pinned}">Always on top ${pinned?'on':'off'}</button><button class="vv-btn" type="button" data-operator="save" ${ready(s,'save_session')&&!pending?'':'disabled'}>Save session</button>`;
  }
  function navigation(s,mark=''){
    const op=s.session?.control?.operator,recovery=s.session?.control?.recovery;
    const label=['available','invalid'].includes(recovery?.status)?'Recovery needs a choice':op?.saved?.saved_at?`Saved ${new Date(op.saved.saved_at).toLocaleTimeString()}`:op?'Browse sessions':'Prepare speech setup to browse';
    return `<button type="button" class="vv-sessions-launch" data-operator="open" aria-label="Saved sessions" aria-haspopup="dialog" ${ready(s,'list_sessions')?'':'disabled'}>${mark}<span class="vv-sessions-nav-text">Saved sessions<small>${escape(label)}</small></span></button>`;
  }
  function recoveryNotice(s){
    const recovery=s.session?.control?.recovery;
    if(!['available','invalid'].includes(recovery?.status))return '';
    return `<div class="vv-recovery-prompt" role="status"><span>${recovery.status==='invalid'?'Saved session needs attention.':'Saved session available.'} Choose Resume or Start new before listening.</span><button type="button" class="vv-btn" data-operator="recovery" ${ready(s,'list_sessions')?'':'disabled'}>Choose session</button></div>`;
  }
  function safety(s,showWorship=true){
    const op=s.session?.control?.operator;if(!op)return '';
    return `${op.worship&&showWorship?'<span class="vv-badge">Worship on</span>':''}<button class="vv-btn vv-emergency" type="button" data-operator="emergency" ${ready(s,'emergency_save')?'':'disabled'}>${op.emergency&&op.busy?'Stopping & saving…':'Emergency Stop & Save'}</button>`;
  }
  async function send(action,value={}){
    if(pending&&action!=='emergency_save')return;
    const s=get();if(!ready(s,action)){notice='This action is unavailable. Reconnect or wait for the current operation.';refresh();return;}
    notice='Requesting…';pending={action};refresh();
    try{
      const result=await window.verseviewDesktop.operator(s.session.session_id,action,value);
      pending={...result,hostId:s.session.control.id};
      setTimeout(()=>{if(pending?.id===result.id){notice='No acknowledgement received. Check the session state before trying again.';pending=null;refresh();}},12000);
    }catch(error){notice=error.message;pending=null;}
    refresh();
  }
  function sync(){
    const s=get(),c=s.session?.control,op=c?.operator;
    if(pending?.id){
      const result=c?.results.find(r=>r.id===pending.id);
      if(c?.id!==pending.hostId){notice='Connection changed. Refresh the sessions before acting.';pending=null;}
      else if(result){notice=['failed','rejected'].includes(result.outcome)?result.reason:'';pending=null;}
    }
    if(!dialog?.open)return;
    const key=JSON.stringify([op,c?.recovery,c?.pending,s.connection,c?.state,pending,notice]);
    if(key===signature)return;signature=key;
    const library=op?.library,selected=library?.selected;
    const disabled=pending||s.connection!=='connected';
    const active=document.activeElement?.getAttribute('data-focus-key');
    const scroll=dialog.querySelector('.vv-session-reader')?.scrollTop||0;
    dialog.innerHTML=`<div class="vv-panel-head"><h2 id="vv-sessions-title">Saved sessions</h2><button class="vv-btn" type="button" data-operator="close" data-focus-key="close" autofocus>Close</button></div><div class="vv-verse-safety"><button class="vv-btn" type="button" data-live-stop ${ready(s,'stop')?'':'disabled'}>Stop listening</button>${safety(s)}</div>${c?.pending.length?window.observerView.controls(s):''}<p class="vv-caption">Opening a session is read-only. Resume prepares its context; press Start listening separately.</p><p class="vv-caption" role="status">${escape(notice||op?.message||library?.message||'')}</p>${c?.recovery&&['available','invalid','staged'].includes(c.recovery.status)?window.observerView.recovery(s,Boolean(disabled)):''}<div class="vv-session-browser"><nav aria-label="Saved session list">${library?.rows.length?library.rows.map(r=>`<button class="vv-btn vv-session-row" type="button" data-operator="preview" data-record="${r.id}" data-focus-key="${r.id}" ${disabled||r.kind==='invalid'?'disabled':''}><strong>${escape(r.saved_at?new Date(r.saved_at).toLocaleString():'Unreadable record')}</strong><span>${r.kind==='session'?'Resumable session':r.kind==='transcript'?'Text archive':'Unreadable · retained'} · ${escape(r.reason)}</span></button>`).join(''):'<p class="vv-caption">No saved sessions in the library yet.</p>'}<div class="vv-control-actions"><button class="vv-btn" type="button" data-operator="list" data-page="${Math.max(0,(library?.page||0)-1)}" ${disabled||!library?.page?'disabled':''}>Previous</button><button class="vv-btn" type="button" data-operator="list" data-page="${(library?.page||0)+1}" ${disabled||!library?.more?'disabled':''}>More sessions</button></div></nav><section class="vv-session-reader" tabindex="0" aria-label="Saved session preview">${selected?`<h3>${selected.kind==='session'?'Session preview':'Text archive'}</h3>${['primary','secondary'].map(role=>`<h4>${escape(role==='primary'?'Primary':'Secondary')} · ${escape(languages[selected.languages[role]]||'Language not stored')} ${selected.sources[role]==='context'?'(engine context)':''}</h4><pre lang="${escape(selected.languages[role]||'und')}">${escape(selected[role]||'No text stored for this stream.')}</pre>`).join('')}<p class="vv-caption">${escape(selected.references.join(' · '))}</p>${selected.outline?`<h4>Saved outline</h4><pre>${escape(selected.outline)}</pre>`:''}<div class="vv-control-actions"><button class="vv-btn" type="button" data-operator="text-page" data-offset="${Math.max(0,selected.offset-4000)}" ${disabled||!selected.offset?'disabled':''}>Earlier text</button><button class="vv-btn" type="button" data-operator="text-page" data-offset="${selected.offset+4000}" ${disabled||!selected.more?'disabled':''}>Later text</button>${selected.resumable?`<button class="vv-btn vv-btn-primary" type="button" data-operator="resume" ${disabled||!ready(s,'resume_saved')?'disabled':''}>Prepare to resume</button>`:'<span class="vv-caption">Text archives cannot restore engine context.</span>'}</div>${c.state!=='stopped'?'<p class="vv-caption">Stop listening before preparing another session.</p>':''}`:'<p class="vv-caption">Select a dated session to read it.</p>'}</section></div>`;
    dialog.querySelector('.vv-session-reader')?.scrollTo({top:scroll});
    if(active)dialog.querySelector(`[data-focus-key="${active}"]`)?.focus();
  }
  function open(button){
    opener=button;
    if(!dialog){dialog=document.createElement('dialog');dialog.className='vv-session-dialog';dialog.setAttribute('aria-labelledby','vv-sessions-title');root.append(dialog);dialog.addEventListener('close',()=>{signature='';const target=opener?.isConnected&&opener.getClientRects().length?opener:[...root.querySelectorAll('[data-operator="open"]')].find(b=>!b.disabled&&b.getClientRects().length);target?.focus();});}
    signature='';dialog.showModal();sync();dialog.querySelector('[autofocus]')?.focus();send('list_sessions',{page:0});
  }
  root.addEventListener('preview:observer',sync);
  root.addEventListener('preview:backend',sync);
  root.addEventListener('click',async event=>{
    const button=event.target.closest('[data-operator]');if(!button||button.disabled)return;
    const action=button.dataset.operator,s=get(),op=s.session?.control?.operator;
    if(action==='open'||action==='recovery'){open(button);return;}
    if(action==='close'){dialog.close();return;}
    if(action==='pin'){
      try{pinned=(await window.verseviewDesktop.setAlwaysOnTop(!pinned)).alwaysOnTop;notice='';}catch(error){notice=error.message;}refresh();return;
    }
    if(action==='emergency'){window.consumerFlow?.cancel();send('emergency_save');return;}
    if(action==='worship'){send('set_worship',{enabled:!op.worship});return;}
    if(action==='save'){send('save_session');return;}
    if(action==='list')send('list_sessions',{page:Number(button.dataset.page)});
    if(action==='preview')send('preview_session',{record_id:button.dataset.record,page:0});
    if(action==='text-page'&&op.library.selected)send('preview_session',{record_id:op.library.selected.id,page:Number(button.dataset.offset)});
    if(action==='resume'&&op.library.selected)send('resume_saved',{record_id:op.library.selected.id,record_revision:op.library.selected.revision});
  });
  window.verseviewDesktop?.windowState?.().then(value=>{pinned=value.alwaysOnTop===true;refresh();}).catch(()=>{});
  window.operatorTools=Object.freeze({render,safety,header,navigation,recoveryNotice});
})();
