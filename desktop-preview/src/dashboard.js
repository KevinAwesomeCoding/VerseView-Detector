(()=>{
  const root=document.getElementById('verseview-prototype');
  const observing=()=>window.previewShell.getMode()==='observer';
  const connectionNotice=()=>window.observerView.connectionNotice(window.previewShell.getObserver());
  const themes={
    sage:{name:'Sage',description:'Soft sage · follows system',preview:['#edf1ea','#fff','#247e69']},
    midnight:{name:'Midnight',description:'Matte charcoal & indigo',preview:['#111319','#242834','#6c7ce0']},
    glass:{name:'Glass',description:'Frosted blue & lavender',preview:['linear-gradient(130deg,#c1d1f1,#c9e6dc)','rgba(255,255,255,.64)','#5281a7']},
    galaxy:{name:'Galaxy',description:'Violet, indigo & starlight',preview:['linear-gradient(130deg,#161129,#51306b)','#30243f','#ad7ef2']},
    aurora:{name:'Aurora',description:'Deep teal & northern blues',preview:['linear-gradient(130deg,#14463f,#24365c)','#1e3a45','#58bfb5']},
    ember:{name:'Ember',description:'Warm amber · follows system',preview:['#f3e8d7','#fffaf3','#aa5a20']}
  };
  const validTheme=key=>Object.prototype.hasOwnProperty.call(themes,key);
  const streamInfo={primary:{name:'English',language:'en',tag:'EN',role:'Primary'},secondary:{name:'Malayalam',language:'ml',tag:'ML',role:'Secondary'}};
  const initial=()=>({view:'session',listening:true,streamOn:{primary:true,secondary:true},reference:'John 3:16',outputStream:'primary',samples:{primary:'next',secondary:'next'},threshold:90,device:'Default microphone (sample)',provider:'Deepgram · English',secondaryProvider:'Sarvam · Malayalam',pending:null,queue:null,seconds:8,serial:2,lastAccepted:{'John 3:16':0},acceptedBy:{'John 3:16':'primary'},partials:{primary:'The passage tells us about God’s love…',secondary:'ദൈവത്തിന്റെ സ്നേഹത്തെക്കുറിച്ച്…'},feedback:'Both sample engines are listening. Their transcripts stay separate; verse delivery is shared.',transcript:[{text:'Let’s turn to John chapter three, verse sixteen.',ref:'John 3:16',result:'Reference detected · command accepted',time:'10:24:00',kind:'ok',stream:'primary',id:'DEMO-001'},{text:'യോഹന്നാൻ മൂന്നാം അധ്യായം പതിനാറാം വാക്യം.',ref:'John 3:16',result:'Same reference · duplicate suppressed',time:'10:24:02',kind:'muted',stream:'secondary',id:'DEMO-002'}],events:[{id:'DEMO-002',ref:'John 3:16',outcome:'Duplicate suppressed',reason:'English already delivered this reference. Shared duplicate protection prevents a second command.',time:'10:24:02',stream:'secondary'},{id:'DEMO-001',ref:'John 3:16',outcome:'Preview updated',reason:'The sample reference and verse text are visible in this prototype.',time:'10:24:00',stream:'primary'},{id:'DEMO-001',ref:'John 3:16',outcome:'Command accepted',reason:'Simulated controller accepted the presentation command.',time:'10:24:00',stream:'primary'}]});
  let state=initial();
  state.theme=window.previewShell.initialTheme;
  const design={radius:16,density:'Comfortable'};
  const verses={
    'John 3:16':'For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life.',
    'John 3:17':'For God sent not his Son into the world to condemn the world; but that the world through him might be saved.',
    'John 3:18':'He that believeth on him is not condemned: but he that believeth not is condemned already, because he hath not believed in the name of the only begotten Son of God.',
    'John 3:19':'And this is the condemnation, that light is come into the world, and men loved darkness rather than light, because their deeds were evil.',
    'John 3:20':'For every one that doeth evil hateth the light, neither cometh to the light, lest his deeds should be reproved.'
  };
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const icon=name=>`<i data-lucide="${name}" aria-hidden="true"></i>`;
  const clock=()=>`10:${String(24+Math.floor(state.seconds/60)).padStart(2,'0')}:${String(state.seconds%60).padStart(2,'0')}`;
  const nextId=()=>`DEMO-${String(++state.serial).padStart(3,'0')}`;
  const sourceFor=id=>state.events.find(e=>e.id===id)?.stream||'primary';
  const sourceName=stream=>`${streamInfo[stream]?.name||'English'} · ${streamInfo[stream]?.role||'Primary'}`;
  const active=stream=>state.listening&&state.streamOn[stream];
  function event(id,ref,outcome,reason,stream){state.events.unshift({id,ref,outcome,reason,time:clock(),stream:stream||sourceFor(id)});state.events=state.events.slice(0,18)}
  function transcript(text,ref,result,kind='ok',stream='primary',id=''){
    state.transcript.push({text,ref,result,time:clock(),kind,stream,id});
    state.transcript=state.transcript.filter((t,i,all)=>all.slice(i+1).filter(l=>l.stream===t.stream).length<3);
    state.partials[stream]='';
  }
  function finalizeTranscript(id,result,kind){for(const line of state.transcript)if(line.id===id){line.result=result;line.kind=kind}}
  function deliver(id,ref){
    const stream=sourceFor(id);
    const last=state.lastAccepted[ref];
    if(typeof last==='number'&&state.seconds-last<60){
      const remaining=60-(state.seconds-last);
      event(id,ref,'Duplicate suppressed',`Already accepted from ${sourceName(state.acceptedBy[ref]||'primary')}. ${remaining}s remain in the shared sample cooldown.`,stream);
      state.feedback=`${ref} suppressed as a duplicate. The preview stays on ${state.reference}.`;
      return false;
    }
    event(id,ref,'Delivery requested','The sample controller received the reference.');
    event(id,ref,'Command accepted','The sample controller accepted the command; this is not a live VerseVIEW confirmation.');
    state.reference=ref;state.lastAccepted[ref]=state.seconds;state.acceptedBy[ref]=stream;state.outputStream=stream;
    event(id,ref,'Preview updated','The simulated presentation preview now shows this reference.');
    state.feedback=`${ref} is now visible in the simulated preview.`;
    return true;
  }
  function runSample(kind,stream='primary'){
    if(!active(stream)){state.feedback=`Resume the ${streamInfo[stream].name} stream before running another sample.`;return}
    state.seconds+=4;
    const id=nextId();
    if(kind==='manual'){
      const ref='John 3:18';
      const text=stream==='secondary'?'പതിനെട്ടാം വാക്യം നോക്കാം.':'And in verse eighteen, we hear the promise again.';
      event(id,ref,'Candidate detected','Sample contextual reference, confidence 83%.',stream);
      if(state.threshold>83){
        if(state.pending){event(state.pending.id,state.pending.ref,'Approval replaced','A new sample candidate replaced the previous held sample.')}
        state.pending={id,ref,stream,text};
        event(id,ref,'Awaiting approval',`Confidence 83% is below the ${state.threshold}% demo threshold.`);
        transcript(text,ref,'Held for your approval','held',stream,id);
        state.feedback=`${ref} is held for approval. The preview has not changed.`;
      }else{
        const accepted=deliver(id,ref);
        transcript(text,ref,accepted?'Reference detected · command accepted':'Duplicate suppressed',accepted?'ok':'muted',stream,id);
      }
    }else if(kind==='range'){
      const ref='John 3:19';
      event(id,ref,'Candidate detected','Sample explicit range: John 3:19–20.',stream);
      const accepted=deliver(id,ref);
      if(accepted){
        if(state.queue)event(state.queue.id,state.queue.ref,'Queue replaced','A new sample range replaced the old queue.');
        state.queue={id:nextId(),ref:'John 3:20',stream};
        event(state.queue.id,state.queue.ref,'Queued','Waiting for a simulated spoken-text match.',stream);
        state.feedback='John 3:19 is visible. John 3:20 is queued; try “Read next verse.”';
      }
      transcript(stream==='secondary'?'യോഹന്നാൻ മൂന്നാം അധ്യായം പത്തൊൻപതു മുതൽ ഇരുപതു വരെയുള്ള വാക്യങ്ങൾ.':'John chapter three, verses nineteen through twenty.',ref,accepted?'Range detected · next verse queued':'Duplicate suppressed',accepted?'ok':'muted',stream,id);
    }else if(kind==='speech'){
      transcript(stream==='secondary'?'ദൈവത്തിന്റെ സ്നേഹം എല്ലാവർക്കും വേണ്ടിയുള്ളതാണ്.':'God’s love reaches every one of us.',null,'Transcript only · no reference detected','muted',stream,id);
      event(id,null,'Transcript only','Sample speech contained no Bible reference; the output stays unchanged.',stream);
      state.feedback=`${streamInfo[stream].name} transcript updated. No reference detected; the presentation preview is unchanged.`;
    }else{
      const ref='John 3:17';
      event(id,ref,'Candidate detected','Sample explicit reference from the simulated speech transcript.',stream);
      const accepted=deliver(id,ref);
      transcript(stream==='secondary'?'യോഹന്നാൻ മൂന്നാം അധ്യായം പതിനേഴാം വാക്യം.':'John chapter three, verse seventeen.',ref,accepted?'Reference detected · command accepted':'Duplicate suppressed',accepted?'ok':'muted',stream,id);
    }
  }
  const nav=()=>`<nav class="vv-nav" aria-label="Dashboard navigation">${[['session','radio','Live session'],['activity','list-filter','Activity'],...(observing()?[['outline','notebook-pen','Outline']]:[]),['testing','flask-conical','Test area'],['settings','sliders-horizontal','Settings']].map(([view,i,label])=>`<button class="cursor-interaction" type="button" data-action="view" data-view="${view}" aria-current="${state.view===view?'page':'false'}">${icon(i)}${label}</button>`).join('')}</nav>`;
  const brand=()=>`<div class="vv-brand"><span class="vv-brand-mark" aria-hidden="true">v</span><span>VerseView<span style="display:block;font-size:9px;letter-spacing:2px;color:var(--vv-muted);margin-top:-3px">DETECTOR</span></span></div>`;
  const button=(action,label,i='',primary=false,extra='')=>`<button type="button" class="vv-btn cursor-interaction ${primary?'vv-btn-primary':''}" data-action="${action}" ${extra}>${i?icon(i):''}${label}</button>`;
  function themePicker(prefix){return `<div class="vv-theme-control">${icon('palette')}<label class="vv-live-announcement" for="${prefix}-theme">Color theme</label><select id="${prefix}-theme" class="vv-theme-select cursor-interaction" data-setting="theme" aria-label="Color theme">${Object.entries(themes).map(([key,t])=>`<option value="${key}" ${state.theme===key?'selected':''}>${t.name}</option>`).join('')}</select></div>`}
  function appearance(){return `<section class="vv-panel vv-appearance" aria-label="Appearance settings"><div class="vv-panel-head"><h2>Appearance</h2><span class="vv-badge">${themes[state.theme].name}</span></div><div class="vv-theme-grid">${Object.entries(themes).map(([key,t])=>`<button type="button" class="vv-theme-option cursor-interaction" data-action="theme" data-theme-choice="${key}" aria-label="${t.name} theme" aria-pressed="${state.theme===key}"><span class="vv-theme-mini" style="--preview-bg:${t.preview[0]};--preview-panel:${t.preview[1]};--preview-accent:${t.preview[2]}" aria-hidden="true"><span class="vv-theme-mini-sidebar"></span><span class="vv-theme-mini-main"><span></span><span></span><span></span></span></span><span class="vv-theme-name">${t.name}${state.theme===key?icon('check'):'<span style="width:16px;height:16px" aria-hidden="true"></span>'}</span><span class="vv-theme-description">${t.description}</span></button>`).join('')}</div><p class="vv-theme-note">Changes the detector interface. VerseVIEW presentation themes are separate.</p></section>`}
  const sourceBadge=stream=>`<span class="vv-source" data-stream="${stream}">${streamInfo[stream]?.tag||'EN'} · ${streamInfo[stream]?.role||'Primary'}</span>`;
  function output(){return `<section class="vv-panel vv-output" aria-label="Simulated presentation preview"><div class="vv-output-top"><span class="vv-eyebrow">Presentation preview</span><span class="vv-badge">English · KJV</span></div><div class="vv-output-ref">${esc(state.reference)}</div><blockquote class="vv-verse" style="padding:0">${esc(verses[state.reference])}</blockquote><div class="vv-output-foot"><span class="vv-output-status">${icon('check')}Command accepted · ${esc(streamInfo[state.outputStream]?.name||'English')}</span><span>Preview only</span></div></section>`}
  function detectionNotice(stream){
    const line=state.transcript.filter(t=>t.stream===stream).at(-1);
    if(!line?.ref)return `<div class="vv-ref-notice"><span class="vv-caption">No reference detected</span></div>`;
    const held=line.kind==='held',duplicate=/duplicate/i.test(line.result),dismissed=/dismissed/i.test(line.result);
    const label=held?'Awaiting approval':duplicate?'Duplicate · not sent':dismissed?'Dismissed':'Command accepted';
    return `<div class="vv-ref-notice"><span><span class="vv-ref-notice-label">Reference detected</span><span class="vv-ref-notice-ref">${esc(line.ref)}</span></span><span class="vv-badge ${!held&&!duplicate&&!dismissed?'vv-ok':''}">${icon(held?'clock-3':duplicate?'copy-check':dismissed?'minus':'check')}${label}</span></div>`;
  }
  function transcriptPanel(prefix,stream){
    const info=streamInfo[stream],listening=active(stream),provider=stream==='primary'?state.provider:state.secondaryProvider;
    const lines=state.transcript.filter(t=>t.stream===stream);
    return `<section class="vv-panel vv-stream" data-speech-stream="${stream}" aria-label="${info.name} speech output">
      <div class="vv-stream-header"><div><h2 ${stream==='secondary'?'lang="ml"':''}>${stream==='secondary'?'മലയാളം':'English'}</h2><p class="vv-stream-provider">${stream==='secondary'?'Malayalam · ':''}${esc(provider.split(' · ')[0])}</p></div><div class="vv-stream-controls"><span class="vv-badge ${listening?'vv-ok':''}"><span class="vv-dot"></span>${listening?'Sample active':'Paused'}</span><button type="button" class="vv-btn vv-icon-btn cursor-interaction" data-action="toggle-stream" data-stream="${stream}" aria-label="${state.streamOn[stream]?'Pause':'Resume'} ${info.name} stream">${icon(state.streamOn[stream]?'pause':'play')}</button></div></div>
      <div class="vv-stream-results">${lines.map(t=>`<div class="vv-transcript-line"><time class="vv-transcript-time">${esc(t.time)}</time><p lang="${info.language}">${esc(t.text)}</p></div>`).join('')}</div>
      ${state.partials[stream]&&listening?`<div class="vv-partial"><p lang="${info.language}">${esc(state.partials[stream])}</p></div>`:''}
      ${detectionNotice(stream)}
    </section>`;
  }
  function approval(){
    const p=state.pending,stream=p?.stream||'primary';
    if(!p)return '';
    return `<section class="vv-panel" aria-label="Manual verse approval"><div class="vv-panel-head"><h2>Review reference</h2><span class="vv-badge" style="color:var(--vv-warn)">83% confidence</span></div><div class="vv-approval-body"><p class="vv-caption">${esc(streamInfo[stream].name)} speech</p><div class="vv-approval-ref">${esc(p.ref)}</div><p class="vv-caption" lang="${streamInfo[stream].language}">“${esc(p.text||'And in verse eighteen…')}”</p><div class="vv-approval-actions">${button('approve','Approve & show','check',true)}${button('reject','Dismiss')}</div></div></section>`;
  }
  function queue(){if(!state.queue)return '';return `<section class="vv-panel" aria-label="Queued references"><div class="vv-panel-head"><h2>Up next</h2><span class="vv-badge">Queued</span></div><div class="vv-queue-row"><span>${esc(state.queue.ref)}</span><span class="vv-result is-held">${icon('clock-3')}Waiting for speech</span></div><div class="vv-queue-note">${sourceBadge(state.queue.stream||'primary')}<p class="vv-caption" style="margin-top:8px">Waiting for the matching verse reading.</p></div></section>`}
  function session(prefix){
    if(observing())return window.observerView.session(window.previewShell.getObserver(),prefix);
    const transcripts=`<section class="vv-stream-section" aria-label="Dual speech recognition output"><div class="vv-dual-grid">${transcriptPanel(prefix,'primary')}${transcriptPanel(prefix,'secondary')}</div></section>`;
    const shared=`<div class="vv-output-layout ${state.pending||state.queue?'has-actions':''}">${output()}${state.pending||state.queue?`<div class="vv-column">${approval()}${queue()}</div>`:''}</div><div class="vv-session-actions">${button('activity','View activity','arrow-up-right')}</div>`;
    return prefix.endsWith('focus')?shared+transcripts:transcripts+shared;
  }
  function testing(prefix){
    if(observing())return window.observerView.testGate();
    return `<section aria-label="Sample speech test area"><div class="vv-test-intro"><p class="vv-caption">Generate sample speech here, then review the result in Live session.</p>${button('run-both','Run both samples','audio-lines',true,active('primary')||active('secondary')?'':'disabled')}</div><div class="vv-dual-grid">${['primary','secondary'].map(stream=>{
      const info=streamInfo[stream],last=state.transcript.filter(t=>t.stream===stream).at(-1);
      return `<section class="vv-panel vv-test-card" data-test-stream="${stream}" aria-label="${info.name} sample controls"><div class="vv-section-title"><h2>${info.name}</h2>${sourceBadge(stream)}</div><div><label for="${prefix}-${stream}-sample">Sample phrase</label><select id="${prefix}-${stream}-sample" class="vv-select cursor-interaction" data-setting="sample" data-stream="${stream}">${[['next','John 3:17 · next verse'],['repeat','John 3:17 · repeat'],['manual','John 3:18 · uncertain'],['range','John 3:19–20 · range'],['speech','Speech without a reference']].map(([v,l])=>`<option value="${v}" ${state.samples[stream]===v?'selected':''}>${l}</option>`).join('')}</select></div><div class="vv-approval-actions">${button('run','Run sample','play',true,`data-stream="${stream}" ${active(stream)?'':'disabled'}`)}${button('toggle-stream',state.streamOn[stream]?'Pause stream':'Resume stream',state.streamOn[stream]?'pause':'play',false,`data-stream="${stream}"`)}</div><div class="vv-test-result"><span class="vv-ref-notice-label">Latest result</span>${esc(last?.ref||'Speech')} · ${esc(last?.result||'Ready')}</div></section>`;
    }).join('')}</div><div class="vv-panel vv-test-summary"><div><p>Current preview: <span style="font-weight:500">${esc(state.reference)}</span></p><p class="vv-caption">${state.pending?'Approval needed for '+esc(state.pending.ref):state.queue?'Queued: '+esc(state.queue.ref):'Sample data only · no live connections'}</p></div><div class="vv-approval-actions">${state.queue?button('read-next','Read next verse','book-open',false,active(state.queue.stream||'primary')?'':'disabled'):''}${button('view',state.pending?'Review reference':'View live session','arrow-up-right',false,'data-view="session"')}</div></div></section>`;
  }
  function activity(){return `<section class="vv-panel"><div class="vv-panel-head"><h2>Delivery activity</h2><span class="vv-pill">Sample events</span></div>${state.events.map(e=>`<div class="vv-activity-item"><span class="vv-dot ${/accepted|updated/i.test(e.outcome)?'vv-ok':''}"></span><div><div class="vv-activity-title">${esc(e.ref||'Speech')} · ${esc(e.outcome)}</div><div class="vv-activity-meta">${sourceBadge(e.stream||'primary')} <span>${esc(e.id)} · ${/Queued|match/i.test(e.outcome)?'RANGE QUEUE':'DEMO DETECTOR'}</span></div><p class="vv-activity-why">${esc(e.reason)}</p></div><span class="vv-time">${esc(e.time)}</span></div>`).join('')}</section>`}
  function settings(prefix){return `<div class="vv-settings-grid"><section class="vv-panel"><div class="vv-panel-head"><h2>Audio & recognition</h2>${icon('audio-lines')}</div><div class="vv-setting"><label for="${prefix}-device">Shared microphone input</label><select class="vv-select cursor-interaction" data-setting="device" id="${prefix}-device">${['Default microphone (sample)','USB mixer input (sample)'].map(d=>`<option ${state.device===d?'selected':''}>${d}</option>`).join('')}</select><p class="vv-caption">One sample audio source feeds both speech engines.</p></div><div class="vv-setting"><label for="${prefix}-provider">Primary · English</label><select class="vv-select cursor-interaction" data-setting="provider" id="${prefix}-provider">${['Deepgram · English','Google · English'].map(d=>`<option ${state.provider===d?'selected':''}>${d}</option>`).join('')}</select></div><div class="vv-setting"><label for="${prefix}-secondary-provider">Secondary · Malayalam</label><select class="vv-select cursor-interaction" data-setting="secondaryProvider" id="${prefix}-secondary-provider">${['Sarvam · Malayalam','Google · Malayalam'].map(d=>`<option ${state.secondaryProvider===d?'selected':''}>${d}</option>`).join('')}</select><p class="vv-caption">Sample configuration only. No audio or provider connection.</p></div></section><section class="vv-panel"><div class="vv-panel-head"><h2>Shared delivery safeguards</h2>${icon('shield-check')}</div><div class="vv-setting"><label for="${prefix}-threshold">Approval threshold <span class="vv-threshold" style="float:right">${state.threshold}%</span></label><input class="cursor-interaction" id="${prefix}-threshold" data-setting="threshold" type="range" min="50" max="100" step="1" value="${state.threshold}"><p class="vv-caption">The uncertain sample is 83% confident. This threshold applies to both sample streams.</p></div><div class="vv-setting"><div class="vv-setting-title">Duplicate protection · shared</div><p class="vv-caption">The same reference heard by both engines within 60 sample seconds produces one presentation command.</p></div><div class="vv-setting"><div class="vv-setting-title">Output Bible · English KJV</div><p class="vv-caption">Speech recognition language is separate from the presentation’s Bible language.</p></div><div class="vv-setting"><div class="vv-setting-title">Preview settings only</div><p class="vv-caption">Your installed detector and presentation output are untouched.</p></div></section></div>`}
  function desktopInfo(){
    const env=window.previewShell.getEnvironment();
    return `<section class="vv-panel preview-about" aria-label="Desktop preview information"><h2>Desktop preview</h2><p class="vv-caption">${esc(env.appearance?.reason||'Preparing window appearance')}</p><p class="vv-caption">Version ${esc(env.version)} · ${env.packaged?'Packaged application':'Development preview'} · ${esc(env.platform)}</p><p class="vv-caption">Build: ${esc(env.buildId||'development')}</p><p class="vv-caption">Appearance, layout, and source choice are saved. Observations come from the detector; samples reset on launch.</p></section>`;
  }
  function health(){return `<div class="vv-health" aria-label="Simulated connection status">${['primary','secondary'].map(stream=>`<span class="vv-badge ${active(stream)?'vv-ok':''}"><span class="vv-dot"></span>${streamInfo[stream].name} ${active(stream)?'sample active':'paused'}</span>`).join('')}<span class="vv-badge vv-ok"><span class="vv-dot"></span>Presentation simulated</span><span class="vv-meter-wrap"><span class="vv-badge">Sample audio</span><span class="vv-meter ${state.listening?'':'is-paused'}" role="img" aria-label="Simulated shared audio input level">${[4,8,12,15,11,7,12,9,5,7].map((h,i)=>`<span style="height:${h}px;opacity:${i>6?.3:.8}"></span>`).join('')}</span></span></div>`}
  function render(){
    designRender();
    const scrollTop=root.querySelector('[data-layout]')?.scrollTop||0;
    const focused=root.contains(document.activeElement)?{layout:document.activeElement.closest('[data-layout]')?.dataset.layout,action:document.activeElement.dataset.action,view:document.activeElement.dataset.view,setting:document.activeElement.dataset.setting,stream:document.activeElement.dataset.stream,themeChoice:document.activeElement.dataset.themeChoice}:null;
    for(const app of root.querySelectorAll('[data-layout]')){
      const prefix=`vv-${app.dataset.layout}`;
      const titles={session:'Live session',activity:'Delivery activity',outline:'Sermon outline',testing:'Test area',settings:'Settings'};
      const subtitles=observing()?{session:'Speech streams, candidate decisions, and delivery status',activity:'Structured events from the detector',outline:'Editable notes and an optional separate display',testing:'Samples stay separate from live observations',settings:'Appearance, speech, and VerseVIEW connection'}:{session:'Sample audio · English and Malayalam',activity:'Detection, approval, and delivery details',testing:'Sample speech · no microphone required',settings:'Audio, recognition, and delivery'};
      app.innerHTML=`<div class="vv-shell"><aside class="vv-sidebar">${brand()}<div><div class="vv-eyebrow vv-nav-label">Workspace</div>${nav()}</div><div class="vv-sidebar-foot"><p>${observing()?'Detector connection':'Rehearsal workspace'}</p><p>${observing()?'Local engine feed':'Sample data only'}</p></div></aside>
        <main class="vv-main"><div class="vv-narrow-nav">${brand()}${nav()}</div><header class="vv-topline"><div><h1>${titles[state.view]||titles.session}</h1><p class="vv-subtitle">${subtitles[state.view]||subtitles.session}</p></div><div class="vv-live-controls">${themePicker(prefix)}${observing()?'<span class="vv-pill">Local feed</span>':button('toggle',state.listening?'Pause demo':'Resume demo',state.listening?'pause':'play',!state.listening)}</div></header>
        <div class="vv-content">${state.view==='session'?session(prefix):state.view==='activity'?(observing()?window.observerView.activity(window.previewShell.getObserver()):activity()):state.view==='outline'&&observing()?window.observerView.outline(window.previewShell.getObserver()):state.view==='testing'?testing(prefix):appearance()+(observing()?window.observerView.settings(window.previewShell.getObserver()):settings(prefix))+desktopInfo()}</div>
        <div class="${state.view==='session'?'vv-live-announcement':'vv-feedback'}" role="status" aria-live="polite">${state.view==='session'?'':icon('info')}<span data-connection-notice>${esc(observing()?connectionNotice():state.feedback)}</span></div><footer class="vv-foot"><span>${observing()?'Desktop preview · live observer':'Desktop preview · sample data only'}</span><span>${observing()?'Delivery guards remain in the engine':'No microphone or VerseVIEW connection'}</span></footer></main></div>`;
      app.scrollTop=scrollTop;
    }
    window.detectorSettings?.syncControls();
    window.liveOutline?.syncControls();
    if(globalThis.lucide)lucide.createIcons({attrs:{width:16,height:16}});
    if(focused?.layout){
      const app=root.querySelector(`[data-layout="${focused.layout}"]`);
      let el;
      const visibleMatch=selector=>[...app.querySelectorAll(selector)].find(candidate=>candidate.getClientRects().length>0);
      const sourceSelector=focused.stream?`[data-stream="${focused.stream}"]`:'';
      if(focused.setting)el=visibleMatch(`[data-setting="${focused.setting}"]${sourceSelector}`);
      else if(focused.action)el=visibleMatch(`[data-action="${focused.action}"]${sourceSelector}${focused.view?`[data-view="${focused.view}"]`:''}${focused.themeChoice?`[data-theme-choice="${focused.themeChoice}"]`:''}`);
      if(el&&!el.disabled)el.focus({preventScroll:true});
    }
  }
  function designRender(){root.dataset.theme=validTheme(state.theme)?state.theme:'sage';root.style.setProperty('--vv-radius',`${design.radius}px`);root.style.setProperty('--vv-gap',design.density==='Compact'?'12px':'20px');root.style.removeProperty('--vv-accent');window.previewShell.setTheme(state.theme)}
  root.addEventListener('click',e=>{
    const b=e.target.closest('button[data-action]');if(!b||b.disabled)return;
    const previousView=state.view;
    const a=b.dataset.action;
    if(a==='sample-mode'){window.previewShell.setMode('samples');return}
    if(observing()&&!['view','theme','activity'].includes(a))return;
    if(a==='view')state.view=b.dataset.view;
    else if(a==='theme'&&validTheme(b.dataset.themeChoice)){state.theme=b.dataset.themeChoice;state.feedback=`${themes[state.theme].name} theme selected.`}
    else if(a==='activity')state.view='activity';
    else if(a==='toggle'){state.listening=!state.listening;state.feedback=state.listening?'Demo resumed. Choose a sample phrase to continue.':'Demo paused. No sample speech will be processed.'}
    else if(a==='toggle-stream'){const stream=b.dataset.stream;state.streamOn[stream]=!state.streamOn[stream];state.feedback=`${streamInfo[stream].name} stream ${state.streamOn[stream]?'resumed':'paused'}. The other stream keeps its own state.`}
    else if(a==='run'){const stream=b.dataset.stream||'primary';runSample(state.samples[stream],stream)}
    else if(a==='run-both'){for(const stream of ['primary','secondary'])if(active(stream))runSample('next',stream);state.feedback=`Sample streams processed separately. Shared presentation preview: ${state.reference}. See Activity for each decision.`}
    else if(a==='try-manual'){const stream=active('primary')?'primary':'secondary';state.samples[stream]='manual';runSample('manual',stream)}
    else if(a==='approve'&&state.pending){const p=state.pending;state.seconds+=2;event(p.id,p.ref,'Operator approved','You approved the held sample reference.',p.stream||'primary');const accepted=deliver(p.id,p.ref);finalizeTranscript(p.id,accepted?'Approved · command accepted':'Approved · duplicate suppressed',accepted?'ok':'muted');state.pending=null}
    else if(a==='reject'&&state.pending){const p=state.pending;event(p.id,p.ref,'Operator dismissed','The sample reference was dismissed without changing the preview.',p.stream||'primary');finalizeTranscript(p.id,'Dismissed · output unchanged','muted');state.pending=null;state.feedback=`${p.ref} dismissed. The preview is unchanged.`}
    else if(a==='read-next'&&state.queue&&active(state.queue.stream||'primary')){
      const q=state.queue;state.seconds+=4;
      const stream=q.stream||'primary';
      transcript(stream==='secondary'?'തിന്മ ചെയ്യുന്നവൻ വെളിച്ചത്തെ വെറുക്കുന്നു.':verses[q.ref],q.ref,'Simulated text match · queue released','ok',stream,q.id);
      event(q.id,q.ref,'Sample text matched','Simulated semantic match to the queued verse; no model was called.',stream);
      if(deliver(q.id,q.ref))state.queue=null;
    }
    render();
    if(previousView!==state.view)root.querySelector('[data-layout]').scrollTop=0;
  });
  root.addEventListener('change',e=>{
    const key=e.target.dataset.setting;if(!key)return;
    if(observing()&&key!=='theme')return;
    if(key==='threshold')state.threshold=Number(e.target.value);
    else if(key==='theme'&&validTheme(e.target.value))state.theme=e.target.value;
    else if(key==='sample')state.samples[e.target.dataset.stream||'primary']=e.target.value;
    else if(['device','provider','secondaryProvider'].includes(key))state[key]=e.target.value;
    if(key!=='sample')state.feedback='Preview settings updated. Installed application settings are unchanged.';
    render();
  });
  root.addEventListener('input',e=>{if(e.target.dataset.setting==='threshold'){state.threshold=Number(e.target.value);root.querySelectorAll('.vv-threshold').forEach(el=>el.textContent=`${state.threshold}%`)}});
  root.addEventListener('preview:layout',()=>{render();root.querySelector('[data-layout]').scrollTop=0});
  root.addEventListener('preview:environment',render);
  root.addEventListener('preview:mode',()=>{if(!observing()&&state.view==='outline')state.view='session';render();root.querySelector('[data-layout]').scrollTop=0});
  let observerRefreshPending=false;
  // Patch only observer content. Keep theme/navigation controls and unchanged
  // source selectors in place while provider events arrive. No remote HTML is
  // accepted: observerView escapes all feed text before producing this markup.
  function patchObserverNode(current,next){
    if(current.nodeType!==next.nodeType||current.nodeName!==next.nodeName){current.replaceWith(next.cloneNode(true));return}
    if(current.nodeType===Node.TEXT_NODE){if(current.data!==next.data)current.data=next.data;return}
    if(current.nodeType!==Node.ELEMENT_NODE||current.isEqualNode(next))return;
    const sameDetailsIdentity=current.tagName==='DETAILS'&&
      (current.dataset.suggestionSession||current.dataset.recoveryKey||'')===(next.dataset.suggestionSession||next.dataset.recoveryKey||'');
    for(const attribute of [...current.attributes]){
      if(!next.hasAttribute(attribute.name)&&!(sameDetailsIdentity&&attribute.name==='open'))current.removeAttribute(attribute.name);
    }
    for(const attribute of next.attributes)if(current.getAttribute(attribute.name)!==attribute.value)current.setAttribute(attribute.name,attribute.value);
    for(let index=0;index<next.childNodes.length;index++){
      if(current.childNodes[index])patchObserverNode(current.childNodes[index],next.childNodes[index]);
      else current.append(next.childNodes[index].cloneNode(true));
    }
    while(current.childNodes.length>next.childNodes.length)current.lastChild.remove();
  }
  function observerRefresh(){
    if(!observing())return;
    const notice=root.querySelector('[data-connection-notice]');
    if(notice&&notice.textContent!==connectionNotice())notice.textContent=connectionNotice();
    window.detectorSettings?.updateAvailability(window.previewShell.getObserver());
    window.cloudSettings?.updateAvailability(window.previewShell.getObserver());
    window.liveOutline?.updateAvailability(window.previewShell.getObserver());
    window.observerView.updateRecoveryAvailability(window.previewShell.getObserver());
    const selection=window.getSelection();
    if(selection&&!selection.isCollapsed&&root.contains(selection.anchorNode)){
      // A copied transcript must not freeze Stop or leave stale approvals enabled.
      const controls=root.querySelector('.vv-engine-control');
      if(controls&&!controls.contains(selection.anchorNode)){
        const nextControls=document.createElement('div');
        nextControls.innerHTML=window.observerView.controls(window.previewShell.getObserver());
        const replacement=nextControls.querySelector('.vv-engine-control');
        if(replacement)patchObserverNode(controls,replacement);
        else controls.remove();
      }
      observerRefreshPending=true;return;
    }
    observerRefreshPending=false;
    const content=root.querySelector('.vv-content');
    if(!content||state.view==='testing')return;
    const snapshot=window.previewShell.getObserver();
    const next=document.createElement('div');next.className='vv-content';
    next.innerHTML=state.view==='session'?window.observerView.session(snapshot,`vv-${root.querySelector('[data-layout]').dataset.layout}`):state.view==='activity'?window.observerView.activity(snapshot):state.view==='outline'?window.observerView.outline(snapshot):appearance()+window.observerView.settings(snapshot)+desktopInfo();
    const surface=root.querySelector('[data-layout]'),scrollTop=surface.scrollTop;
    patchObserverNode(content,next);
    window.detectorSettings?.syncControls();
    window.liveOutline?.syncControls();
    if(globalThis.lucide)lucide.createIcons({attrs:{width:16,height:16}});
    surface.scrollTop=scrollTop;
  }
  root.addEventListener('preview:observer',observerRefresh);
  root.addEventListener('preview:backend',observerRefresh);
  document.addEventListener('selectionchange',()=>{if(observerRefreshPending)observerRefresh()});
  root.addEventListener('preview:reset',()=>{
    const {theme,threshold,device,provider,secondaryProvider}=state;
    state={...initial(),theme,threshold,device,provider,secondaryProvider};
    state.feedback='Sample session reset. Appearance and sample configuration kept.';
    render();
    root.querySelector('[data-layout]').scrollTop=0;
  });
  render();
})();
