(() => {
  'use strict';
  const root=document.getElementById('verseview-prototype');
  const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let draft=null,target='windowed',output={open:false,displays:[]},outputNotice='',outputBusy=false;
  const dirty=()=>draft&&draft.text!==draft.base;
  const refresh=()=>root.dispatchEvent(new Event('preview:observer'));
  function reset(snapshot){
    const session=snapshot.session,value=session?.control?.outline;
    draft=value?{hostId:session.control.id,sessionId:session.session_id,revision:value.revision,text:value.text,base:value.text,
      conflict:false,submission:null,notice:''}:null;
  }
  function sync(snapshot){
    const session=snapshot.session,value=session?.control?.outline;
    if(!value)return;
    if(!draft){reset(snapshot);return;}
    if(draft.hostId!==session.control.id||draft.sessionId!==session.session_id){
      if(dirty()){draft.conflict=true;draft.notice='Detector session changed. Your draft is retained; reload before saving.';return;}
      reset(snapshot);return;
    }
    const result=session.control.results.find(row=>row.id===draft.submission?.id);
    if(result){
      draft.submission=null;draft.notice=result.reason;
      if(result.outcome==='saved'){
        draft.text=draft.base=value.text;draft.revision=value.revision;draft.conflict=false;
      }
    }
    if(value.revision!==draft.revision){
      if(dirty()||draft.conflict||root.querySelector('[data-outline-text]')===document.activeElement)draft.conflict=true;
      else{draft.text=draft.base=value.text;draft.revision=value.revision;draft.conflict=false;}
    }
  }
  function canEdit(snapshot){
    const session=snapshot.session,control=session?.control;
    return snapshot.connection==='connected'&&!!draft&&draft.hostId===control?.id&&draft.sessionId===session.session_id&&
      ['stopped','running'].includes(control.state)&&control.actions.includes('edit_outline')&&!draft.submission;
  }
  function render(snapshot){
    sync(snapshot);
    const value=snapshot.session?.control?.outline;
    if(!value||!draft)return '<section class="vv-panel preview-about"><h2>Sermon outline</h2><p class="vv-caption">Outline notes require the bundled backend. Nothing is displayed automatically.</p></section>';
    const editable=canEdit(snapshot);
    const status=!value.active?'Recognition stopped. Notes remain available.':!value.enabled?'AI outline is off. You can edit notes manually.':
      !value.provider_ready?'AI outline is enabled but its LLM analysis or provider is unavailable. Check private backend settings.':
      value.status==='generating'?'Generating outline notes…':'AI outline waits for sufficient new speech and checks about every 90 seconds.';
    const targets=[['windowed','Windowed preview'],...output.displays.map(d=>[d.id,`${d.label}${d.primary?' · Primary':''} · ${d.width}×${d.height}`])];
    const targetAvailable=targets.some(([id])=>id===target);
    if(!targetAvailable)targets.push([target,'Unavailable display · choose another']);
    return `<section class="vv-panel vv-outline" aria-label="Sermon outline notes"><div class="vv-panel-head"><h2>Outline notes</h2><span class="vv-pill">${value.source==='model'?'AI generated':value.source==='manual'?'Operator edited':'No notes yet'}</span></div>
      <p class="vv-caption">${escape(status)} Model updates preserve newer operator edits. Notes are session memory; closing the backend clears them.</p>
      <label for="outline-notes">Notes · up to 4,000 characters</label><textarea id="outline-notes" data-outline-text maxlength="4000" ${editable?'':'disabled'}>${escape(draft.text)}</textarea>
      <p class="vv-caption" role="status" data-outline-status>${escape(draft.conflict?'Notes changed while you were editing. Your draft is retained. Reload the latest notes before saving.':draft.submission?'Saving notes…':value.message||draft.notice||(dirty()?'Unsaved edits.':'No unsaved edits.'))}</p>
      <div class="vv-control-actions"><button type="button" class="vv-btn vv-btn-primary" data-outline-save ${!editable||!dirty()||draft.conflict?'disabled':''}>Save notes</button><button type="button" class="vv-btn" data-outline-reload ${draft.submission?'disabled':''}>Reload latest notes</button></div>
      <div class="vv-outline-display"><h3>Separate outline display</h3><p class="vv-caption">Choose a window or attached monitor, then open it explicitly. This output shows notes separately from VerseVIEW verses.</p>
      <label for="outline-target">Output target</label><select id="outline-target" data-outline-target ${outputBusy?'disabled':''}>${targets.map(([id,label])=>`<option value="${escape(id)}" ${id===target?'selected':''}>${escape(label)}</option>`).join('')}</select>
      <div class="vv-control-actions"><button type="button" class="vv-btn" data-outline-open ${snapshot.connection!=='connected'||!value.text.trim()||outputBusy||!targetAvailable?'disabled':''}>Open outline display</button><button type="button" class="vv-btn" data-outline-close ${!output.open||outputBusy?'disabled':''}>Close outline display</button></div>
      <p class="vv-caption" role="status" data-outline-output-status>${escape(outputNotice||output.message||(output.open?'Outline window is open. Escape closes it.':'Outline output is closed.'))}</p></div></section>`;
  }
  function updateAvailability(snapshot){
    sync(snapshot);
    const text=root.querySelector('[data-outline-text]'),save=root.querySelector('[data-outline-save]');
    if(text)text.disabled=!canEdit(snapshot);
    if(save)save.disabled=!canEdit(snapshot)||!dirty()||!!draft?.conflict;
    const open=root.querySelector('[data-outline-open]');
    if(open)open.disabled=outputBusy||snapshot.connection!=='connected'||!snapshot.session?.control?.outline?.text.trim()||
      (target!=='windowed'&&!output.displays.some(d=>d.id===target));
  }
  function syncControls(){
    const text=root.querySelector('[data-outline-text]');
    if(text&&draft&&text!==document.activeElement&&text.value!==draft.text)text.value=draft.text;
    const select=root.querySelector('[data-outline-target]');if(select)select.value=target;
  }
  root.addEventListener('input',event=>{
    if(!event.target.matches('[data-outline-text]')||!draft)return;
    draft.text=event.target.value;draft.notice='';refresh();
  });
  root.addEventListener('change',event=>{if(event.target.matches('[data-outline-target]')){target=event.target.value;outputNotice='';refresh();}});
  root.addEventListener('click',async event=>{
    const button=event.target.closest('[data-outline-save],[data-outline-reload],[data-outline-open],[data-outline-close]');
    if(!button||button.disabled||window.previewShell.getMode()!=='observer')return;
    const snapshot=window.previewShell.getObserver();
    if(button.matches('[data-outline-reload]')){reset(snapshot);refresh();return;}
    if(button.matches('[data-outline-save]')){
      if(!canEdit(snapshot)||draft.conflict||!dirty())return;
      const selected=draft;selected.submission={id:null};refresh();
      try{
        const submitted=await window.verseviewDesktop.editOutline(snapshot.session.session_id,selected.revision,selected.text);
        selected.submission=submitted;
        setTimeout(()=>{
          if(selected.submission?.id===submitted.id){selected.submission=null;selected.conflict=true;selected.notice='No save acknowledgement. Reload the latest notes before trying again.';refresh();}
        },12000);
      }catch{selected.submission=null;selected.conflict=true;selected.notice='Could not save notes. Reload the latest version before trying again.';}
      refresh();return;
    }
    outputBusy=true;outputNotice='';refresh();
    try{
      output=button.matches('[data-outline-close]')?await window.verseviewDesktop.closeOutlineOutput():
        await window.verseviewDesktop.openOutlineOutput(snapshot.session.session_id,target);
    }catch{outputNotice='Could not open or close output. Refresh its session and display target.';}
    finally{outputBusy=false;refresh();}
  });
  window.liveOutline=Object.freeze({render,updateAvailability,syncControls});
  if(window.verseviewDesktop){
    const changed=value=>{output=value;refresh();};
    window.verseviewDesktop.onOutlineOutputChanged(changed);
    window.verseviewDesktop.outlineOutputState().then(changed).catch(()=>{});
  }
})();
