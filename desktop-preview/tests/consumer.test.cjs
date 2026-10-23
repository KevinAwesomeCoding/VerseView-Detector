'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=name=>fs.readFileSync(path.join(__dirname,'../src',name),'utf8');
function events(){const listeners={};return {dataset:{},addEventListener:(n,f)=>(listeners[n]??=[]).push(f),removeEventListener:(n,f)=>{listeners[n]=(listeners[n]||[]).filter(v=>v!==f);},dispatchEvent:e=>{for(const f of [...listeners[e.type]||[]])f(e);},listeners};}
function snapshot(){return {connection:'connected',message:'Connected',sources:[],session:{session_id:'a'.repeat(32),pid:123,origin:'microphone',engine_state:'running',host:{managed:true},history_available:true,
 config:{streams:{primary:{language:'en',provider:'deepgram',enabled:true},secondary:{language:'ml',provider:'sarvam',enabled:false}}},streams:{primary:{state:'transcript_received'}},transcripts:[{id:'speech',stream:'primary',language:'en',text:'John 3:16',is_final:true,timestamp:'2026-10-20T12:00:00Z'}],
 delivery_events:[{candidate_id:'INTERNAL-CANDIDATE',reference:'John 3:16',stream:'primary',language:'en',source:'FAST-PATH',stage:'command',outcome:'COMMAND_ACCEPTED',timestamp:'2026-10-20T12:00:00Z',reason:'Accepted'}],control:{id:'b'.repeat(32),state:'running',actions:['stop','panic'],results:[],pending:[{candidate_id:'INTERNAL-HELD',reference:'John 3:18',stream:'primary',source:'SEMANTIC-EXTRACT',confidence:.7}],recovery:{status:'none'}}}};}
function observerHarness(){
 const root=events(),s=snapshot();let dev=false;
 const window={previewShell:{isDeveloper:()=>dev,getObserver:()=>s,getMode:()=> 'observer',getBackend:()=>({status:'ready',owned:true,pid:123})},transcriptView:{controls:()=>'<button>Full transcript</button>',isFull:()=>false},cloudSettings:{render:()=>''},detectorSettings:{render:()=>''},consumerFlow:{state:()=>({})}};
 const document={getElementById:()=>root,addEventListener:()=>{},querySelectorAll:()=>[]};
 vm.runInNewContext(source('observer.js'),{window,document,Event,setTimeout:()=>{}});
 return {s,window,root,view:window.observerView,developer:v=>dev=v};
}
const visible=html=>html.replace(/<[^>]*>/g,' ');
test('normal Live keeps approvals, truthful delivery and transcript switch without technical identifiers or disabled stream',()=>{
 const h=observerHarness();let text=visible(h.view.session(h.s,'vv-studio'));
 for(const expected of ['John 3:16','Command sent','Approve','Dismiss','John 3:18','Full transcript'])assert.match(text,new RegExp(expected));
 assert.doesNotMatch(text,/INTERNAL|FAST-PATH|SEMANTIC-EXTRACT|PID|Standalone backend|Local feed|മലയാളം/);
 const live=h.view.session(h.s,'vv-studio');assert.ok(live.indexOf('Reference result')<live.indexOf('Observed speech streams'));assert.ok(live.indexOf('Observed speech streams')<live.indexOf('Reference decisions'));
 assert.doesNotMatch(text,/verse.*visible|screen.*verified/i);
 h.s.session.config.streams.secondary.enabled=true;
 assert.match(h.view.session(h.s,'vv-studio'),/data-speech-stream="secondary"/);
 h.developer(true);text=visible(h.view.session(h.s,'vv-studio'));assert.match(text,/INTERNAL-HELD/);assert.match(text,/PID 123/);
});
test('normal History consolidates candidate stages and distinguishes duplicate, held and queued from sent',()=>{
 const h=observerHarness(),base=h.s.session.delivery_events[0];
 h.s.session.delivery_events=[{...base,outcome:'DETECTED'},{...base},{...base,candidate_id:'duplicate',outcome:'SUPPRESSED',reason:'Duplicate cooldown'},{...base,candidate_id:'queued',outcome:'QUEUED'},{...base,candidate_id:'held',outcome:'MANUAL_CONFIRM_REQUIRED'}];
 const html=h.view.history(h.s),text=visible(html);
 assert.equal((html.match(/vv-history-row/g)||[]).length,4);
 assert.match(text,/Already sent recently/);assert.match(text,/Waiting for the verse reading/);assert.match(text,/Needs approval/);assert.doesNotMatch(text,/INTERNAL|FAST-PATH|COMMAND_ACCEPTED/);
});
test('accepted verse highlights its source speech and History links to that transcript row',()=>{
 const h=observerHarness(),event=h.s.session.delivery_events[0];
 Object.assign(event,{transcript_id:'speech',trigger_text:'John 3:16'});
 const live=h.view.session(h.s,'vv-studio'),history=h.view.history(h.s);
 assert.match(live,/data-transcript-id="speech"/);
 assert.match(live,/<mark>John 3:16<\/mark>/);
 assert.match(history,/data-show-transcript="speech"/);
 assert.match(history,/“John 3:16”/);
 event.trigger_text='<unsafe>';
 assert.doesNotMatch(h.view.history(h.s),/<unsafe>/);
});
test('Live explicitly labels suppressed references and explains why without claiming a send',()=>{
 const h=observerHarness(),base=h.s.session.delivery_events[0];
 h.s.session.delivery_events=[{...base,outcome:'DETECTED'},{...base,outcome:'SUPPRESSED',reason:'No book, chapter or verse anchor'}];
 const html=h.view.session(h.s,'vv-studio'),text=visible(html);
 assert.match(text,/Reference suppressed/);assert.match(text,/Suppressed · not sent/);
 assert.match(text,/Not sent\. No book, chapter or verse anchor/);
 assert.doesNotMatch(text,/Reference detected|Command sent|Last sent:/);
 h.s.session.delivery_events[1].reason='<script>unsafe</script>';
 assert.doesNotMatch(h.view.session(h.s,'vv-studio'),/<script>unsafe/);
 h.s.session.delivery_events[1].reason='Duplicate cooldown';
 assert.match(visible(h.view.session(h.s,'vv-studio')),/Already sent recently/);
});
test('normal settings and diagnostics are separate; stale feed never says listening',()=>{
 const h=observerHarness();assert.doesNotMatch(h.view.settings(h.s),/PID|VERSEVIEW_|Session aaaa|Local detector connection/);
 h.s.connection='stale';assert.match(h.view.compactControls(h.s),/Connection unavailable/);assert.doesNotMatch(h.view.compactControls(h.s),/>Listening</);
 h.s.connection='connected';h.s.session.streams.primary.state='error';assert.match(h.view.consumerNotice(h.s),/speech recognition needs attention/);
 h.developer(true);assert.match(h.view.runtime(h.s),/PID 123/);
});
test('top controls keep urgent actions visible and group occasional actions in More actions',()=>{
 const h=observerHarness(),c=h.s.session.control;
 c.actions.push('set_ask_before_sending');c.ask_before_sending=false;
 h.window.operatorTools={safety:()=>'<button data-operator="emergency">Emergency Stop & Save</button>',header:()=>'<button data-operator="worship">Worship</button><button data-operator="pin">Always on top</button><button data-operator="save">Save session</button>',render:()=>'',recoveryNotice:()=>''};
 const html=h.view.compactControls(h.s);
 assert.match(html,/<button[^>]*data-live-stop/);
 assert.match(html,/<button[^>]*data-ask-before-send[^>]*aria-pressed="false"/);
 assert.match(html,/<button[^>]*data-operator="emergency"/);
 assert.match(html,/<details[^>]*data-control-menu><summary[^>]*>More actions<\/summary>/);
 assert.ok(html.indexOf('data-control-menu')<html.indexOf('data-new-session'));
 assert.ok(html.indexOf('data-control-menu')<html.indexOf('data-engine-action="panic"'));
 assert.ok(html.indexOf('data-control-menu')<html.indexOf('data-operator="save"'));
 c.ask_before_sending=true;
 assert.match(h.view.compactControls(h.s),/data-ask-before-send aria-pressed="true"[^>]*>Ask before sending <strong>On<\/strong>/);
});
function flowHarness(){
 const root=events(),s=snapshot();s.session.control.state='stopped';s.session.control.pending=[];s.session.control.actions=['start'];
 const calls=[];let backend={status:'idle',owned:false};
 const window={previewShell:{getObserver:()=>s,getBackend:()=>backend,getMode:()=> 'observer'},verseviewDesktop:{launchBackend:async()=>{calls.push('launch');backend={status:'ready',owned:true};return {status:'ready',pid:123};}},observerView:{start:async()=>calls.push('start')}};
 vm.runInNewContext(source('consumer.js'),{window,document:{getElementById:()=>root},Event,setTimeout,clearTimeout});
 return {s,calls,root,flow:window.consumerFlow,backend:v=>backend=v};
}
test('Start prepares once and waits for a fresh matching observer and completed sync before one guarded start',async()=>{
 const h=flowHarness();h.s.connection='waiting';h.s.session.control.sync={status:'pulling'};
 const pending=h.flow.prepare(true);await new Promise(setImmediate);assert.deepEqual(h.calls,['launch']);
 h.s.connection='connected';h.root.dispatchEvent(new Event('preview:observer'));await new Promise(setImmediate);assert.deepEqual(h.calls,['launch']);
 await h.flow.prepare(true);assert.deepEqual(h.calls,['launch'],'another click while preparing does not retry');
 h.s.session.control.sync.status='complete';h.root.dispatchEvent(new Event('preview:observer'));await pending;
 assert.deepEqual(h.calls,['launch','start']);assert.equal(h.flow.state().busy,false);
});
test('recovery, failed sync, missing start permission and disconnected owned backend never start',async()=>{
 for(const scenario of ['recovery','sync','actions','stale']){
  const h=flowHarness();if(scenario==='recovery')h.s.session.control.recovery={status:'available'};
  if(scenario==='sync')h.s.session.control.sync={status:'failed'};
  if(scenario==='actions')h.s.session.control.actions=[];
  if(scenario==='stale'){h.s.connection='stale';h.backend({status:'ready',owned:true});}
  await h.flow.prepare(true);assert.deepEqual(h.calls,[],scenario);assert.ok(h.flow.state().notice);
 }
 const h=flowHarness();await h.flow.prepare(false);assert.deepEqual(h.calls,[],'preparing Settings never starts listening');
});
test('Developer Mode defaults off, rejects saved sample source until opted in, persists and returns to live',()=>{
 const root=events(),nodes={};const storage={theme:'galaxy',layout:'focus',mode:'samples'};
 for(const id of ['preview-surface','preview-layout','preview-mode','preview-reset'])nodes[id]={...events(),classList:{toggle:()=>{}}};
 const window={};let saved;
 vm.runInNewContext(source('desktop.js'),{window,document:{getElementById:id=>id==='verseview-prototype'?root:nodes[id]},localStorage:{getItem:()=>JSON.stringify(storage),setItem:(k,v)=>saved=JSON.parse(v)},Event,CustomEvent:class extends Event{constructor(n,v){super(n);this.detail=v.detail;}}});
 assert.equal(window.previewShell.isDeveloper(),false);assert.equal(window.previewShell.getMode(),'observer');
 window.previewShell.setMode('samples');assert.equal(window.previewShell.getMode(),'observer');
 window.previewShell.setDeveloper(true);window.previewShell.setMode('samples');assert.equal(window.previewShell.getMode(),'samples');
 window.previewShell.setDeveloper(false);assert.equal(saved.developer,false);assert.equal(saved.mode,'observer');assert.equal(saved.theme,'galaxy');assert.equal(saved.layout,'focus');
});
test('cancelling preparation while waiting for sync prevents a later automatic start',async()=>{
 const h=flowHarness();h.s.session.control.sync={status:'pulling'};
 const pending=h.flow.prepare(true);await new Promise(setImmediate);h.flow.cancel();await pending;
 h.s.session.control.sync.status='complete';h.root.dispatchEvent(new Event('preview:observer'));
 assert.deepEqual(h.calls,[]);assert.equal(h.flow.state().busy,false);assert.match(h.flow.state().notice,/cancelled/);
});
test('dashboard gates developer pages and keeps Stop on History and Settings while listening',()=>{
 const h=observerHarness(),app={dataset:{layout:'studio'},scrollTop:0,innerHTML:'',querySelectorAll:()=>[]};let dev=false,mode='observer';
 Object.assign(h.root,{style:{setProperty:()=>{},removeProperty:()=>{}},contains:()=>false,querySelectorAll:s=>s==='[data-layout]'?[app]:[],querySelector:s=>s.includes('[data-layout]')?app:null});
 Object.assign(h.window.previewShell,{initialTheme:'glass',isDeveloper:()=>dev,getMode:()=>mode,getLayout:()=> 'studio',setTheme:()=>{},getEnvironment:()=>({version:'test'}),setDeveloper:value=>{dev=value;if(!dev)mode='observer';h.root.dispatchEvent(new Event('preview:developer'));}});
 Object.assign(h.window.detectorSettings,{syncControls:()=>{},updateAvailability:()=>{}});h.window.cloudSettings.updateAvailability=()=>{};
 vm.runInNewContext(source('dashboard.js'),{window:h.window,document:{getElementById:()=>h.root,activeElement:null,addEventListener:()=>{}},Event});
 const navigate=view=>h.root.dispatchEvent({type:'click',target:{closest:selector=>selector==='button[data-action]'?{dataset:{action:'view',view}}:null}});
 assert.match(app.innerHTML,/data-view="activity"[^>]*>.*History/);assert.doesNotMatch(app.innerHTML,/data-view="runtime"|data-view="testing"|Local feed/);
 navigate('testing');assert.match(app.innerHTML,/<h1>Live<\/h1>/,'hidden pages cannot be navigated to');
 navigate('activity');assert.match(app.innerHTML,/Reference history/);assert.match(app.innerHTML,/data-live-stop/);
 navigate('settings');assert.match(app.innerHTML,/data-developer-mode/);assert.match(app.innerHTML,/data-live-stop/);
 h.window.previewShell.setDeveloper(true);assert.match(app.innerHTML,/data-view="runtime"/);navigate('build');assert.match(app.innerHTML,/Desktop preview information/);
 h.window.previewShell.setDeveloper(false);assert.match(app.innerHTML,/<h1>Live<\/h1>/);assert.doesNotMatch(app.innerHTML,/data-view="build"/);
});
test('normal Connections submits only write-only replacements and sync URL, preserving hidden cloud tuning',async()=>{
 const root=events(),policy=require('../src/cloud-policy.js'),values={enabled:true,routes:Object.fromEntries(Object.entries(policy.routes).map(([k,v])=>[k,v[0]])),watcher_min_gap:20,limits:policy.ceilings,confirmed:['groq','gemini','cloudflare'],sync_url:'',credentials:{deepgram_api_key:true}};
 const s={connection:'connected',session:{session_id:'a'.repeat(32),host:{managed:true},control:{id:'b'.repeat(32),state:'stopped',actions:['save_settings'],results:[],settings:{revision:'c'.repeat(32),cloud:values}}}};
 const field={dataset:{cloudCredential:'deepgram_api_key'},value:'WRITE-ONLY-TEST-KEY'};let submitted;
 root.querySelectorAll=selector=>selector==='[data-cloud-credential]'?[field]:[];
 const window={cloudPolicy:policy,previewShell:{isDeveloper:()=>false,getObserver:()=>s},verseviewDesktop:{saveSettings:async(...args)=>{submitted=JSON.parse(JSON.stringify(args));return{id:'d'.repeat(32)};}}};
 vm.runInNewContext(source('cloud-settings.js'),{window,document:{getElementById:()=>root},Event});
 const html=window.cloudSettings.render(s);assert.match(html,/Deepgram speech key · Configured/);assert.doesNotMatch(html,/data-cloud-route|data-cloud-confirm|data-cloud-limit|qwen\//);
 await root.listeners.submit[0]({target:{matches:()=>true},preventDefault:()=>{}});
 const change=submitted[2].cloud_settings;assert.deepEqual(Object.keys(change).sort(),['credentials','sync_url']);assert.equal(change.credentials.deepgram_api_key,'WRITE-ONLY-TEST-KEY');assert.equal(field.value,'');assert.doesNotMatch(html,/WRITE-ONLY-TEST-KEY/);
});
test('an explicitly closed backend can be prepared again even while its last snapshot is fresh',async()=>{
 const h=flowHarness();h.s.session.control.state='closed';h.backend({status:'closed',owned:false});
 await h.flow.prepare(false);assert.deepEqual(h.calls,['launch']);
});

test('Live speech setup contains languages and stream controls, Settings keeps microphone and target, both remain locked when running',()=>{
 const root=events(),s=snapshot(),policy=require('../src/settings-policy.js');
 root.querySelectorAll=()=>[];
 s.session.control.settings={revision:'c'.repeat(32),devices:[{id:0,label:'Test microphone'}],values:{language:'English',stt_engine:'deepgram',dual_stt_enabled:true,secondary_language:'ml',secondary_stt_engine:'sarvam',mic_index:0,remote_url:'http://127.0.0.1:50010/control.html',bible_translation:'KJV'}};
 s.session.control.state='stopped';s.session.control.actions=['save_settings'];
 const window={settingsPolicy:policy,sessionPolicy:require('../src/session-policy.js'),previewShell:{getMode:()=> 'observer'}};
 vm.runInNewContext(source('settings.js'),{window,document:{getElementById:()=>root},Event,setTimeout});
 const speech=window.detectorSettings.render(s,'speech'),connection=window.detectorSettings.render(s,'settings');
 for(const key of ['language','stt_engine','dual_stt_enabled','secondary_language','secondary_stt_engine']){assert.match(speech,new RegExp('data-detector-setting="'+key+'"'));assert.doesNotMatch(connection,new RegExp('data-detector-setting="'+key+'"'));}
 for(const key of ['mic_index','remote_url','bible_translation']){assert.match(connection,new RegExp('data-detector-setting="'+key+'"'));assert.doesNotMatch(speech,new RegExp('data-detector-setting="'+key+'"'));}
 s.session.control.state='running';const locked=window.detectorSettings.render(s,'speech');
 assert.match(locked,/data-detector-setting="language" disabled/);assert.match(locked,/data-detector-setting="dual_stt_enabled"[^>]*disabled/);
});

test('emergency state replaces stale preparation notices and reports stopped after saving',()=>{
 const h=observerHarness();h.s.session.control.state='stopped';
 h.s.session.control.operator={emergency:true,busy:false,status:'saved',message:'Session saved. Listening is stopped.'};
 h.window.consumerFlow.state=()=>({notice:'Start requested. Waiting for speech readiness.'});
 assert.equal(h.view.consumerNotice(h.s),'Session saved. Listening is stopped.');
 assert.match(h.view.compactControls(h.s),/>Stopped</);
});
