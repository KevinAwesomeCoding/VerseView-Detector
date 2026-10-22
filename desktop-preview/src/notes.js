(() => {
 'use strict';
 const root=document.getElementById('verseview-prototype');
 const escape=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const get=()=>window.previewShell.getObserver(),ready=(s,a)=>s.connection==='connected'&&s.session?.control?.actions.includes(a);
 let pending=null,notice='',exportKind='all',saving=false,dialog,opener;
 const refresh=()=>root.dispatchEvent(new Event('preview:observer'));
 const time=x=>x?new Date(x).toLocaleString():'Not generated';
 async function send(action,value={}){
  const s=get();if(pending||!ready(s,action))return;
  pending={action};notice='Requesting…';refresh();
  try{const result=await window.verseviewDesktop.operator(s.session.session_id,action,value);pending={...result,host:s.session.control.id};
   setTimeout(()=>{if(pending?.id===result.id){pending=null;notice='No acknowledgement received. Review the current state before trying again.';refresh();}},12000);
  }catch(e){pending=null;notice=e.message;}
  refresh();
 }
 function live(s){return s.session?.control?.notes?'<button type="button" class="vv-btn" data-action="view" data-view="notes">Sermon notes</button>':'';}
 function render(s){
  const c=s.session?.control,n=c?.notes,disabled=a=>pending||saving||!ready(s,a)?'disabled':'';
  if(!n)return '<section class="vv-panel"><h2>Sermon notes</h2><p>Prepare speech setup to connect to your session. Listening stays stopped.</p></section>';
  return `<section class="vv-panel vv-notes" aria-label="Sermon notes"><div class="vv-panel-head"><h2>Sermon notes</h2><span class="vv-badge">${escape(n.status)}</span></div><p class="vv-caption">A final summary of a captured session. Live Outline remains separate. Configured summary route: ${escape(n.route)}</p>${c.pending?.length?window.observerView.controls(s):''}<div class="vv-control-actions"><button type="button" class="vv-btn vv-btn-primary" data-notes="generate" ${disabled('generate_notes')}>Generate sermon notes</button><button type="button" class="vv-btn" data-notes="cancel" ${disabled('cancel_notes')}>Cancel generation</button></div><p role="status" class="vv-caption">${escape(notice||n.message||'Generate notes when there is enough speech. Listening can continue during generation.')}${n.busy?' The provider call is still running.':''}</p>${n.busy?`<progress aria-label="Notes request in progress"></progress><p class="vv-caption">${n.request?'Request snapshot '+escape(n.request.source_id)+' · captured '+escape(time(n.request.captured_at)):''}</p>`:''}${n.text?`<p class="vv-caption">Captured ${escape(time(n.captured_at))} · ${n.generated_at?'Generated '+escape(time(n.generated_at)):'Generation time not stored (restored notes)'} · Configured request route: ${escape(n.result_route)}<br>Snapshot ${escape(n.source_id)}. Later speech is excluded from these notes and their combined export.</p><pre class="vv-notes-preview" tabindex="0" aria-label="Generated sermon notes">${escape(n.text)}</pre>`:'<p class="vv-caption">No generated notes yet. Your transcript can be exported without AI.</p>'}<fieldset class="vv-detection-settings"><legend>Export a captured session</legend><label>Include<select data-notes-export-kind>${[['all','Notes, transcript and references'],['notes','Sermon notes'],['transcript','Full current transcript'],['references','Current cited references']].map(([value,label])=>`<option value="${value}" ${value===exportKind?'selected':''}>${label}</option>`).join('')}</select></label><p class="vv-caption">Notes/combined exports use the notes snapshot. Transcript/reference exports capture the current session. Both speech languages and full text are retained; incomplete journals are reported.</p><div class="vv-control-actions"><button type="button" class="vv-btn" data-notes="prepare-export" ${disabled('prepare_export')}>Prepare export</button><button type="button" class="vv-btn" data-notes="save-export" ${saving||!n.export||s.connection!=='connected'?'disabled':''}>${saving?'Saving…':'Choose file and save'}</button></div>${n.export?`<p class="vv-caption">Prepared ${escape(n.export.kind)} · snapshot ${escape(n.export.source_id)}. Choose a destination to save it.</p>`:''}</fieldset><section class="vv-notes-save-status"><h3>Automatic saves</h3><p class="vv-caption">${escape(n.auto.message||'Recovery checkpoints and emergency saves preserve the session without AI. Normal Stop or closing while listening saves a transcript first; automatic notes follow your saved preference. Closing an already stopped app does not make another cloud request.')}</p>${n.auto.saved_at?`<p class="vv-caption">Saved ${escape(time(n.auto.saved_at))} · ${escape(n.auto.status)}</p>`:''}${n.auto.transcript_path?`<p class="vv-caption vv-save-path">Transcript: ${escape(n.auto.transcript_path)}</p>`:''}${n.auto.notes_path?`<p class="vv-caption vv-save-path">Notes: ${escape(n.auto.notes_path)}</p>`:''}</section><details class="vv-memory-tools"><summary>Session memory</summary><p class="vv-caption">Clear working memory after saving a recoverable backup. Stop listening and any remote bot first. This leaves VerseVIEW output, saved sessions, exported files, credentials and diagnostic evidence intact.</p><button type="button" class="vv-btn" data-notes="review-clear" ${disabled('prepare_memory_clear')}>Review Clear Memory</button></details></section>`;
 }
 function sync(){
  const s=get(),c=s.session?.control;
  if(pending?.id){const result=c?.results.find(r=>r.id===pending.id);if(c?.id!==pending.host){pending=null;notice='Connection changed. Review the session before acting.';}else if(result){const action=pending.action;pending=null;notice=['failed','rejected'].includes(result.outcome)?result.reason:'';if(action==='prepare_memory_clear'&&result.outcome==='requested')openReview();}}
  syncButtons();
 }
 function syncButtons(){
  const s=get(),n=s.session?.control?.notes;
  const actions={generate:'generate_notes',cancel:'cancel_notes','prepare-export':'prepare_export','review-clear':'prepare_memory_clear','confirm-clear':'clear_memory'};
  for(const b of root.querySelectorAll('[data-notes]')){
   if(b.dataset.notes==='close-review')continue;
   b.disabled=Boolean(pending)||saving||(b.dataset.notes==='save-export'?s.connection!=='connected'||!n?.export:!ready(s,actions[b.dataset.notes]));
  }
  if(dialog?.open&&(!n?.memory_review||s.connection!=='connected'))dialog.querySelector('[data-notes="confirm-clear"]').disabled=true;
 }
 function openReview(){
  const n=get().session?.control?.notes,r=n?.memory_review;if(!r)return;
  if(!dialog||!dialog.isConnected){dialog=document.createElement('dialog');dialog.className='vv-memory-dialog';dialog.setAttribute('aria-labelledby','vv-memory-title');root.append(dialog);dialog.addEventListener('close',()=>opener?.isConnected&&opener.focus());}
  dialog.innerHTML=`<h2 id="vv-memory-title">Save and clear working memory?</h2><p>${escape(r.scope)}</p><p class="vv-caption">Nothing is cleared if the recoverable save fails. Use Saved sessions to restore the backup.</p><div class="vv-control-actions"><button class="vv-btn" type="button" data-notes="close-review">Keep memory</button><button class="vv-btn" type="button" data-notes="confirm-clear" data-memory-revision="${r.revision}">Save backup and clear memory</button></div>`;
  dialog.showModal();dialog.querySelector('[data-notes="close-review"]').focus();
 }
 root.addEventListener('preview:observer',sync);root.addEventListener('preview:backend',sync);
 root.addEventListener('change',event=>{if(event.target.matches('[data-notes-export-kind]'))exportKind=event.target.value;});
 root.addEventListener('click',async event=>{
  const b=event.target.closest('[data-notes]');if(!b||b.disabled)return;
  const s=get(),n=s.session?.control?.notes;
  if(b.dataset.notes==='generate')send('generate_notes',{revision:n.revision});
  if(b.dataset.notes==='cancel')send('cancel_notes');
  if(b.dataset.notes==='prepare-export')send('prepare_export',{revision:n.revision,kind:exportKind});
  if(b.dataset.notes==='review-clear'){opener=b;send('prepare_memory_clear');}
  if(b.dataset.notes==='close-review')dialog.close();
  if(b.dataset.notes==='confirm-clear'){const revision=b.dataset.memoryRevision;dialog.close();send('clear_memory',{revision});}
  if(b.dataset.notes==='save-export'){
   saving=true;notice='Choose a destination in the Save dialog.';refresh();
   try{const result=await window.verseviewDesktop.exportSession(s.session.session_id,n.export.id);notice=result.message;}catch(e){notice=e.message;}
   saving=false;refresh();
  }
 });
 window.sermonNotes=Object.freeze({render,live,syncButtons});
})();
