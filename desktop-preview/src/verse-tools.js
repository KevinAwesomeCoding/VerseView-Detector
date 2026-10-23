(() => {
  'use strict';
  const root=document.getElementById('verseview-prototype');
  const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const get=()=>window.previewShell.getObserver();
  const ready=(s,a)=>s.connection==='connected'&&s.session?.control?.actions.includes(a);
  const outcomes={COMMAND_ACCEPTED:'Command sent',SUBMITTED:'Checking reference',SUPPRESSED:'Not sent',QUEUED:'Waiting for reading',MANUAL_CONFIRM_REQUIRED:'Needs approval',CANCELLED:'Cancelled',ERROR:'Could not send',DELIVERY_FAILED:'Could not send',DETECTED:'Reference detected',DELIVERY_REQUESTED:'Sending reference',NOT_ACCEPTED:'Not sent',INVALID:'Invalid reference'};
  const tabs={context:'Context',history:'History',chapter:'Chapter'};
  let dialog,opener,tab='context',signature='',pending=null,notice='',host=null;
  let draft={reference:'',context:'',revision:'',book:'John',chapter:'3'};
  function loadContext(v){draft.context=[v.book,v.chapter].filter(Boolean).join(' ')+(v.verse?`:${v.verse}`:'');draft.revision=v.revision;}
  const refresh=()=>root.dispatchEvent(new Event('preview:observer'));
  async function send(action,value){
    const s=get();if(pending||!ready(s,action))return;
    pending={action};notice='Requesting…';refresh();
    try{
      const result=await window.verseviewDesktop.operator(s.session.session_id,action,value);
      pending={...result,host:s.session.control.id};
      setTimeout(()=>{if(pending?.id===result.id){pending=null;notice='No acknowledgement received. Check delivery activity before trying again.';refresh();}},12000);
    }catch(e){pending=null;notice=e.message;}
    refresh();
  }
  function field(key,label,value,extra=''){
    return `<label for="vv-verse-${key}">${label}<input id="vv-verse-${key}" data-verse-field="${key}" value="${escape(value)}" ${extra}></label>`;
  }
  function preview(s){
    const c=s.session?.control,v=c?.verses,selected=v?.selected,last=v?.last_send;
    const disabled=a=>pending||!ready(s,a)?'disabled':'';
    return `${selected?`<h3>${escape(selected.reference)}</h3><p class="vv-caption">${escape(selected.translation.toUpperCase())} · Preview</p><p class="vv-verse-text">${escape(selected.status==='loading'?'Loading text…':selected.status==='stale'?'Selection expired. Preview it again.':selected.text||'Text unavailable in this translation. The reference is validated.')}</p><button type="button" class="vv-btn vv-btn-primary" data-verse="send" data-verse-focus="send" ${disabled('send_reference')||(selected.status==='stale'?'disabled':'')}>Send ${escape(selected.reference)}</button><p class="vv-caption">${c?.operator?.worship?'Worship is on. Presentation will be suppressed.':c?.state==='running'?'The normal approval, duplicate and delivery checks apply.':'Start listening before sending.'}</p>`:'<h3>Verse preview</h3><p class="vv-caption">Preview a reference or select one from history or a chapter.</p>'}${last?`<div class="vv-verse-outcome"><strong>${escape(last.reference)}</strong><p>${escape(outcomes[last.outcome]||'Check delivery activity')}</p><p class="vv-caption">${escape(last.reason)}</p>${root.dataset.developer==='true'?`<code>${escape(last.candidate_id)}</code>`:''}</div>`:''}`;
  }
  function grid(s){
    const g=s.session?.control?.verses?.grid;
    if(!g?.reference)return '<p class="vv-caption">A chapter grid appears when a book and chapter are known.</p>';
    if(!g.count)return `<p class="vv-caption">Verse numbers unavailable for ${escape(g.reference)}.</p>`;
    return `<details class="vv-chapter-grid-panel" data-grid-session="${escape(g.revision)}"><summary>Chapter verses · ${escape(g.reference)} · ${g.count} verses</summary><p class="vv-caption">${escape(g.numbering)} numbering · ${escape(g.note)}</p><div class="vv-chapter-grid" role="group" aria-label="${escape(g.reference)} verse numbers">${Array.from({length:g.count},(_,i)=>`<button type="button" class="vv-btn" data-verse="grid-preview" data-reference="${escape(g.reference)}:${i+1}" data-context-revision="${g.revision}" data-verse-focus="grid-${i+1}" aria-label="Preview ${escape(g.reference)}:${i+1}" ${String(i+1)===g.current?'aria-current="true"':''} ${pending||!ready(s,'grid_preview')?'disabled':''}>${i+1}</button>`).join('')}</div></details>`;
  }
  function live(s){
    const v=s.session?.control?.verses,context=v?.context;
    const available=Boolean(v)&&s.connection==='connected';
    const chapter=[context?.book,context?.chapter].filter(Boolean).join(' ');
    return `<section class="vv-panel vv-live-reference" aria-label="Manual reference"><form class="vv-live-reference-form" data-verse-form="preview">${field('reference','Bible reference',draft.reference,'maxlength="128" placeholder="John 3:16" autocomplete="off"')}<button class="vv-btn" type="submit" ${pending||!ready(s,'verse_preview')?'disabled':''}>Preview reference</button></form><div class="vv-reference-tools"><button type="button" class="vv-btn" data-verse="open" ${available?'':'disabled'}>Verse tools</button><button type="button" class="vv-btn" data-verse="open-chapter" ${available?'':'disabled'}>${escape(chapter?'Chapter · '+chapter:'Browse chapter')}</button>${window.sermonNotes?.live(s)||''}</div><p class="vv-caption" role="status" data-live-verse-notice>${escape(notice||'Preview a reference without changing VerseVIEW. Use Send explicitly to present it.')}</p>${grid(s)}${v?.selected?`<details data-live-reference-preview data-reference-session="${escape(v.selected.id)}" open><summary>Reference preview · ${escape(v.selected.reference)}</summary><div class="vv-live-reference-preview" aria-label="Reference preview">${preview(s)}</div></details>`:''}</section>`;
  }
  function syncControls(){
    const input=root.querySelector('.vv-live-reference [data-verse-field="reference"]');
    if(input&&input!==document.activeElement)input.value=draft.reference;
    const s=get();
    for(const button of root.querySelectorAll('.vv-live-reference button')){
      if(button.dataset.view==='notes')continue;
      const opensTool=['open','open-chapter'].includes(button.dataset.verse);
      button.disabled=Boolean(pending)||(opensTool? s.connection!=='connected'||!s.session?.control?.verses:!ready(s,button.dataset.verse==='send'?'send_reference':button.dataset.verse==='grid-preview'?'grid_preview':'verse_preview'));
      if(button.dataset.verse==='send'&&s.session?.control?.verses?.selected?.status==='stale')button.disabled=true;
    }
  }
  function sync(){
    const s=get(),c=s.session?.control,v=c?.verses;
    if(pending?.id){
      const result=c?.results.find(r=>r.id===pending.id);
      if(c?.id!==pending.host){pending=null;notice='Connection changed. Preview the reference again before sending.';}
      else if(result){pending=null;notice=result.reason;}
    }
    if(!dialog?.open)return;
    if(host!==c?.id){host=c?.id;draft.revision='';notice='Connection changed. Reload context and preview before sending.';}
    const key=JSON.stringify([v,c?.state,c?.operator,c?.pending,c?.actions,s.connection,tab,pending,notice]);
    if(signature===key)return;signature=key;
    const active=document.activeElement,focus=dialog.contains(active)?active.dataset.verseField||active.dataset.verseFocus:null;
    const caret=active?.selectionStart,finish=active?.selectionEnd;
    const scroll=dialog.querySelector('.vv-verse-content')?.scrollTop||0;
    const openGrid=dialog.querySelector('[data-grid-session][open]')?.dataset.gridSession;
    const disabled=a=>pending||!ready(s,a)?'disabled':'';
    let body='';
    if(!v)body='<p>Verse tools are unavailable. Reconnect to the detector.</p>';
    else if(tab==='context')body=`<form data-verse-form="context"><p class="vv-caption">Current context: ${escape([v.context.book,v.context.chapter,v.context.verse].filter(Boolean).join(' · ')||'None')}${v.context.staged?' · Prepared for next Start':''}</p>${field('context','Book, chapter and optional verse',draft.context,'maxlength="128" placeholder="John 3 or John 3:16" autocomplete="off"')}<p class="vv-caption">Context guides continued references. Applying it does not present a verse.</p>${draft.revision!==v.context.revision?'<p class="vv-caption">Context changed while you were editing. Reload before applying.</p>':''}<div class="vv-control-actions"><button class="vv-btn" type="button" data-verse="reload" data-verse-focus="reload">Reload context</button><button class="vv-btn" type="submit" ${disabled('set_context')||(!draft.revision||draft.revision!==v.context.revision?'disabled':'')}>${c.state==='stopped'?'Prepare context':'Apply context'}</button></div></form>`;
    else if(tab==='history')body=`<p class="vv-caption">Accepted commands from this listening session. Select a reference to preview it. Visible output is not confirmed here.</p><button type="button" class="vv-btn" data-verse="clear-history" data-verse-focus="clear-history" ${disabled('clear_history')||(!v.history.length?'disabled':'')}>Clear current history</button><p class="vv-caption">Clears this list only. Saved sessions, sermon references and delivery diagnostics are retained.</p><div class="vv-verse-history">${v.history.length?v.history.slice().reverse().map((r,i)=>`<button class="vv-btn vv-verse-row" type="button" data-verse="select" data-reference="${escape(r.reference)}" data-verse-focus="history-${i}" ${disabled('verse_preview')}><strong>${escape(r.reference)}</strong><span class="vv-caption">${escape(r.time)}</span></button>`).join(''):'<p class="vv-caption">No accepted references in this session yet.</p>'}</div>`;
    else if(tab==='chapter'){
      const ch=v.chapter;
      body=`${grid(s)}<form data-verse-form="chapter"><div class="vv-verse-fields"><label for="vv-verse-book">Book<select id="vv-verse-book" data-verse-field="book">${v.books.map(b=>`<option ${b.name===draft.book?'selected':''}>${escape(b.name)}</option>`).join('')}</select></label>${field('chapter','Chapter',draft.chapter,'inputmode="numeric" maxlength="3"')}</div><button class="vv-btn" type="submit" ${disabled('chapter_browse')}>Browse chapter</button></form>${ch?`<h3>${escape(ch.reference)} · ${escape(ch.translation.toUpperCase())}</h3>${ch.status==='loading'?'<p>Loading chapter…</p>':ch.status==='stale'?'<p>Chapter changed. Browse again.</p>':ch.status==='unavailable'?'<p>Text unavailable in the selected translation.</p>':`<p class="vv-caption">Select a verse to preview it. Nothing is sent automatically.</p>${ch.rows.map((r,i)=>`<button type="button" class="vv-btn vv-verse-row" data-verse="select" data-reference="${escape(r.reference)}" data-verse-focus="chapter-${i}" ${disabled('verse_preview')}><strong>${escape(r.reference)}</strong><span>${escape(r.text)}</span></button>`).join('')}<div class="vv-control-actions"><button type="button" class="vv-btn" data-verse="page" data-page="${ch.page-1}" ${disabled('chapter_browse')||(!ch.page?'disabled':'')}>Previous verses</button><button type="button" class="vv-btn" data-verse="page" data-page="${ch.page+1}" ${disabled('chapter_browse')||(!ch.more?'disabled':'')}>More verses</button></div>`}`:''}`;
    }
    dialog.innerHTML=`<div class="vv-verse-head"><h2 id="vv-verse-title">Verse tools</h2><button class="vv-btn" type="button" data-verse="close" data-verse-focus="close">Close</button></div><div class="vv-verse-safety"><button class="vv-btn" type="button" data-live-stop ${ready(s,'stop')?'':'disabled'}>Stop listening</button>${window.operatorTools?.safety(s)||''}</div><div role="tablist" aria-label="Verse tools" class="vv-verse-tabs">${Object.entries(tabs).map(([id,label])=>`<button type="button" class="vv-btn" role="tab" id="vv-verse-tab-${id}" aria-controls="vv-verse-panel" aria-selected="${tab===id}" tabindex="${tab===id?'0':'-1'}" data-verse="tab" data-tab="${id}" data-verse-focus="tab-${id}">${label}</button>`).join('')}</div><p class="vv-caption vv-verse-notice" role="status">${escape(notice||v?.message||'Previews are read-only. Use Send explicitly to request presentation.')}</p>${c?.pending.length?window.observerView.controls(s):''}<div class="vv-verse-content"><section id="vv-verse-panel" role="tabpanel" aria-labelledby="vv-verse-tab-${tab}" tabindex="0">${body}</section><aside class="vv-verse-preview" aria-label="Selected verse preview">${preview(s)}</aside></div>`;
    dialog.querySelector('.vv-verse-content')?.scrollTo({top:scroll});
    const gridPanel=dialog.querySelector('[data-grid-session]');if(gridPanel&&gridPanel.dataset.gridSession===openGrid)gridPanel.open=true;
    if(focus){const el=dialog.querySelector(`[data-verse-field="${focus}"],[data-verse-focus="${focus}"]`);el?.focus({preventScroll:true});if(typeof caret==='number'&&el?.setSelectionRange)el.setSelectionRange(caret,finish);}
  }
  function open(button,initialTab='context'){
    const v=get().session?.control?.verses;if(!v)return;
    opener=button;host=get().session.control.id;loadContext(v.context);tab=initialTab;
    if(initialTab==='chapter'&&v.context.book&&v.context.chapter){draft.book=v.context.book;draft.chapter=v.context.chapter;}
    if(!dialog){dialog=document.createElement('dialog');dialog.className='vv-verse-dialog';dialog.setAttribute('aria-labelledby','vv-verse-title');root.append(dialog);dialog.addEventListener('close',()=>{signature='';const target=opener?.isConnected&&opener.getClientRects().length?opener:root.querySelector('[data-verse="open"]');target?.focus();});}
    signature='';dialog.showModal();sync();dialog.querySelector('[data-verse="close"]').focus();
  }
  root.addEventListener('preview:observer',sync);root.addEventListener('preview:backend',sync);
  root.addEventListener('input',e=>{const k=e.target.dataset.verseField;if(k)draft[k]=e.target.value;});
  root.addEventListener('change',e=>{const k=e.target.dataset.verseField;if(k)draft[k]=e.target.value;});
  root.addEventListener('submit',e=>{
    const form=e.target.dataset.verseForm;if(!form)return;e.preventDefault();
    if(form==='preview')send('verse_preview',{reference:draft.reference});
    if(form==='context')send('set_context',{reference:draft.context,context_revision:draft.revision});
    if(form==='chapter')send('chapter_browse',{reference:`${draft.book} ${draft.chapter}`,page:0});
  });
  root.addEventListener('keydown',e=>{
    const button=e.target.closest('[role="tab"][data-verse="tab"]');if(!button||!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
    e.preventDefault();const names=Object.keys(tabs),i=names.indexOf(tab);tab=names[e.key==='Home'?0:e.key==='End'?names.length-1:(i+(e.key==='ArrowLeft'?-1:1)+names.length)%names.length];sync();dialog.querySelector(`[data-tab="${tab}"]`).focus();
  });
  root.addEventListener('click',e=>{
    const b=e.target.closest('[data-verse]');if(!b||b.disabled)return;
    const v=get().session?.control?.verses;
    switch(b.dataset.verse){
      case 'open':open(b);break;
      case 'open-chapter':open(b,'chapter');break;
      case 'close':dialog.close();break;
      case 'tab':tab=b.dataset.tab;sync();break;
      case 'reload':if(v){loadContext(v.context);signature='';sync();}break;
      case 'clear-history':if(v?.history_revision)send('clear_history',{history_revision:v.history_revision});break;
      case 'grid-preview':send('grid_preview',{reference:b.dataset.reference,context_revision:b.dataset.contextRevision});break;
      case 'select':send('verse_preview',{reference:b.dataset.reference});break;
      case 'page':if(v?.chapter)send('chapter_browse',{reference:v.chapter.reference,page:Number(b.dataset.page)});break;
      case 'send':if(v?.selected)send('send_reference',{selection_id:v.selected.id});break;
    }
  });
  window.verseTools=Object.freeze({live,syncControls,previewSuggestion:(button,id)=>{open(button);send('preview_suggestion',{suggestion_id:id});},previewDetected:(button,reference)=>{draft.reference=reference;open(button);send('verse_preview',{reference});}});
})();
