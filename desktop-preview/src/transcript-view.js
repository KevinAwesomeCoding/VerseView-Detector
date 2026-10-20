(() => {
  'use strict';
  const root=document.getElementById('verseview-prototype');
  let full=false, history=null;
  try{full=localStorage.getItem('verseview.live-transcript-view')==='full';}catch{}
  const notify=()=>root.dispatchEvent(new Event('preview:observer'));
  function sync(session){
    if(!session)return;
    if(history?.session!==session.session_id)history={session:session.session_id,rows:new Map(),offset:0,busy:false,done:false,error:'',available:session.history_available};
    if(!full||history.busy||history.error||!session.history_available||!window.verseviewDesktop?.transcriptPage)return;
    const owner=history;owner.busy=true;
    window.verseviewDesktop.transcriptPage(owner.session,owner.offset).then(page=>{
      if(history!==owner)return;
      owner.available=page.available;owner.done=page.complete;owner.journalPending=page.pending;
      for(const row of page.rows){if(row.update){const previous=owner.rows.get(row.id);if(previous)previous.translation=row.translation;}else owner.rows.set(row.id,row);}
      owner.offset=page.next;
    }).catch(()=>{if(history===owner)owner.error='Full history could not be loaded. Recent speech is still shown.';})
      .finally(()=>{if(history!==owner)return;owner.busy=false;notify();});
  }
  function rows(session,role){
    const map=new Map(history && history.session===session?.session_id?history.rows:[]);
    for(const row of session?.transcripts||[])if(row.is_final&&!map.has(row.id))map.set(row.id,row);
    return [...map.values()].filter(row=>row.stream===role).sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp));
  }
  function controls(session){
    // Poll newly appended pages only on observer updates, not on a finished empty
    // page notification. This avoids a self-triggered IPC/render loop.
    if(history?.session!==session?.session_id)sync(session);
    const notice=!session?'Start listening to collect the session transcript.':!session.history_available?'Full history is unavailable for this session. Recent speech is shown.':history?.error||(history?.journalPending?'Waiting for the latest transcript to be saved…':!history?.done?'Loading the session from the beginning…':'From the beginning of this listening session.');
    return `<div class="vv-transcript-toolbar" aria-label="Live view"><div role="group" aria-label="Transcript view"><button type="button" class="vv-btn ${!full?'vv-btn-primary':''}" data-transcript-view="focus" aria-pressed="${!full}">Focus</button><button type="button" class="vv-btn ${full?'vv-btn-primary':''}" data-transcript-view="full" aria-pressed="${full}">Full transcript</button></div>${full?'<button type="button" class="vv-btn" data-transcript-jump>Jump to live</button>':''}</div>${full?`<p class="vv-caption" role="status">${notice}</p>`:''}`;
  }
  root.addEventListener('click',e=>{
    const b=e.target.closest('[data-transcript-view]');
    if(b){full=b.dataset.transcriptView==='full';try{localStorage.setItem('verseview.live-transcript-view',full?'full':'focus');}catch{};if(full)sync(window.previewShell.getObserver().session);notify();}
    if(e.target.closest('[data-transcript-jump]'))for(const box of root.querySelectorAll('[data-full-transcript]')){box.scrollTop=box.scrollHeight;box.dataset.follow='true';}
  });
  // Fetch once per actual feed update. A completed page itself may request the
  // next page, but a caught-up empty page must not continually fetch itself.
  let revision='';
  root.addEventListener('preview:observer',()=>{
    const s=window.previewShell?.getObserver().session;
    const key=s?`${s.session_id}:${s.revision}`:'';
    if(full&&root.querySelector('[data-transcript-view]')&&s&&(key!==revision||history&&!history.done&&!history.busy&&!history.error)){
      revision=key;sync(s);
    }
  });
  function beforePatch(){return [...root.querySelectorAll('[data-full-transcript]')].map(e=>({stream:e.dataset.fullTranscript,top:e.scrollTop,follow:e.scrollHeight-e.scrollTop-e.clientHeight<45}));}
  function afterPatch(saved){for(const e of root.querySelectorAll('[data-full-transcript]')){const old=saved.find(v=>v.stream===e.dataset.fullTranscript);e.scrollTop=!old||old.follow?e.scrollHeight:old.top;}}
  window.transcriptView=Object.freeze({isFull:()=>full,rows,controls,beforePatch,afterPatch});
})();
