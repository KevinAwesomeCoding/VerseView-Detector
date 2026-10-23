(() => {
  'use strict';
  const root=document.getElementById('verseview-prototype');
  let full=false, history=null, pendingReveal=null;
  const jumps=new Map();
  const reduceMotion=()=>Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
  function cancelJump(stream){
    const jump=jumps.get(stream);
    if(jump){window.cancelAnimationFrame(jump.frame);jumps.delete(stream);}
  }
  function jumpToLive(box){
    const stream=box.dataset.fullTranscript;
    cancelJump(stream);
    box.dataset.follow='true';
    if(reduceMotion()||!window.requestAnimationFrame){box.scrollTop=box.scrollHeight;return;}
    const jump={from:box.scrollTop,start:null,frame:null};
    jumps.set(stream,jump);
    const step=now=>{
      if(jumps.get(stream)!==jump)return;
      // Observer updates replace the panel DOM. Resolve the current panel on
      // each frame so live updates cannot cancel or snap the movement.
      const current=[...root.querySelectorAll('[data-full-transcript]')].find(e=>e.dataset.fullTranscript===stream);
      if(!current){jumps.delete(stream);return;}
      if(jump.start===null)jump.start=now;
      const progress=reduceMotion()?1:Math.min(1,(now-jump.start)/360);
      const end=Math.max(0,current.scrollHeight-current.clientHeight);
      current.scrollTop=jump.from+(end-jump.from)*(1-Math.pow(1-progress,3));
      if(progress<1)jump.frame=window.requestAnimationFrame(step);
      else jumps.delete(stream);
    };
    jump.frame=window.requestAnimationFrame(step);
  }
  function cancelManualJump(e){
    if(e.type==='keydown'&&!['ArrowUp','ArrowDown','PageUp','PageDown','Home','End',' ','Escape'].includes(e.key))return;
    const box=e.target.closest?.('[data-full-transcript]');
    if(box)cancelJump(box.dataset.fullTranscript);
  }
  for(const type of ['wheel','touchstart','pointerdown','keydown'])root.addEventListener(type,cancelManualJump,{capture:true,passive:true});
  try{full=localStorage.getItem('verseview.live-transcript-view')==='full';}catch{}
  const notify=()=>root.dispatchEvent(new Event('preview:observer'));
  function sync(session){
    if(!session)return;
    if(history?.session!==session.session_id){for(const stream of jumps.keys())cancelJump(stream);history={session:session.session_id,rows:new Map(),offset:0,busy:false,done:false,error:'',available:session.history_available};}
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
    if(b){for(const stream of jumps.keys())cancelJump(stream);full=b.dataset.transcriptView==='full';try{localStorage.setItem('verseview.live-transcript-view',full?'full':'focus');}catch{};if(full)sync(window.previewShell.getObserver().session);notify();}
    if(e.target.closest('[data-transcript-jump]'))for(const box of root.querySelectorAll('[data-full-transcript]'))jumpToLive(box);
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
  function reveal(){
    if(!pendingReveal)return;
    const {id,stream}=pendingReveal;
    const box=[...root.querySelectorAll('[data-full-transcript]')].find(e=>e.dataset.fullTranscript===stream);
    const row=box&&[...box.querySelectorAll('[data-transcript-id]')].find(e=>e.dataset.transcriptId===id);
    if(!row)return;
    pendingReveal=null;
    row.classList.add('vv-transcript-located');
    const top=row.offsetTop-box.offsetTop-(box.clientHeight-row.clientHeight)/2;
    box.scrollTo({top:Math.max(0,top),behavior:reduceMotion()?'instant':'smooth'});
    row.setAttribute('tabindex','-1');row.focus({preventScroll:true});
  }
  function afterPatch(saved){for(const e of root.querySelectorAll('[data-full-transcript]')){const old=saved.find(v=>v.stream===e.dataset.fullTranscript);e.scrollTop=jumps.has(e.dataset.fullTranscript)&&old?old.top:!old||old.follow?e.scrollHeight:old.top;}reveal();}
  function openAt(id,stream){
    if(!id||!['primary','secondary'].includes(stream))return;
    for(const role of jumps.keys())cancelJump(role);
    full=true;pendingReveal={id,stream};
    try{localStorage.setItem('verseview.live-transcript-view','full');}catch{}
    sync(window.previewShell.getObserver().session);
  }
  window.transcriptView=Object.freeze({isFull:()=>full,rows,controls,beforePatch,afterPatch,openAt});
})();
