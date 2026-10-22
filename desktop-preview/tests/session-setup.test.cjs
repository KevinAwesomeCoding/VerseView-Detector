'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),vm=require('node:vm');
const policy=require('../src/session-policy.js'),settings=require('../src/settings-policy.js'),{LaunchPreference}=require('../launch-preferences.cjs');
test('session fields are typed, copied, and unsafe shortcuts/timetables rejected',()=>{
 for(const value of ['Shift+Escape','Control+Shift+P','Meta+Shift+P','Alt+Shift+M','Shift+F8'])assert.equal(policy.shortcut(value),true);
 for(const value of ['Escape','Shift+P','Alt+F4','Control+Shift+I','Meta+Shift+Q','Shift+Control+P'])assert.equal(policy.shortcut(value),false);
 assert.doesNotThrow(()=>settings.validatePatch({service_schedule:[],smart_schedule:true,desktop_panic_shortcut:'Control+Shift+P'}));
 for(const v of [{service_schedule:[{day:9,time:'10:00',language:'English'}]},{service_schedule:[policy.defaults.service_schedule[0],policy.defaults.service_schedule[0]]},{desktop_panic_shortcut:'Escape'},{desktop_transcript_display:'fake'},{auto_start:true}])assert.throws(()=>settings.validatePatch(v));
});
test('display choices use only supplied text and never invent transliteration or original script',()=>{
 const row={text:'Daivam',translation:'God',text_kind:'transliteration',language:'ml'};
 assert.match(policy.transcript(row,'original').label,/script was not supplied/);
 assert.equal(policy.transcript(row,'translation').text,'God');assert.equal(policy.transcript(row,'transliteration').text,'Daivam');
 const raw={text:'ദൈവം',language:'ml'};assert.equal(policy.transcript(raw,'transliteration').text,raw.text);assert.match(policy.transcript(raw,'transliteration').label,/unavailable/);
 assert.match(policy.transcript(raw,'translation').label,/unavailable/);assert.deepEqual(row,{text:'Daivam',translation:'God',text_kind:'transliteration',language:'ml'});
});
test('startup opt-in is local, explicit, schema checked, claimed once, and cancellable',t=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'vv-launch-'));t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));const file=path.join(directory,'launch.json');
 fs.writeFileSync(file,JSON.stringify({auto_start:true}));let p=new LaunchPreference(file,{permission:()=> 'granted'});assert.equal(p.claim().claimed,false);
 p.set(true);assert.equal(p.claim().claimed,false,'enabling does not start in the same app process');
 p=new LaunchPreference(file,{permission:()=> 'denied'});assert.equal(p.snapshot().permission,'denied');assert.equal(p.claim().claimed,true);assert.equal(p.claim().claimed,false);
 p=new LaunchPreference(file);p.cancel();assert.equal(p.claim().claimed,false);p.set(false);assert.equal(new LaunchPreference(file).snapshot().enabled,false);
 assert.throws(()=>p.set('true'));
});
function harness({permission='granted',recovery='none',enabled=true}={}){
 const callbacks={},docCallbacks={},initial=[];let interval;const calls=[];
 const root={addEventListener:(e,f)=>callbacks[e]=f,dispatchEvent:()=>{}};
 const s={connection:'connected',session:{session_id:'a'.repeat(32),control:{actions:['start','panic'],recovery:{status:recovery},settings:{values:{desktop_panic_shortcut:'Control+Shift+P'}}}}};
 const window={sessionPolicy:policy,previewShell:{getObserver:()=>s,getMode:()=> 'observer'},verseviewDesktop:{startup:async(action)=>({enabled,permission,claimed:action==='claim'&&enabled}),clearOutput:async()=>calls.push('panic')},consumerFlow:{prepare:async start=>calls.push(start?'start':'prepare'),cancel:()=>calls.push('cancel')}};
 const document={getElementById:()=>root,querySelector:()=>null,addEventListener:(e,f)=>docCallbacks[e]=f};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../src/session-setup.js'),'utf8'),{window,document,Event,setTimeout:f=>initial.push(f),setInterval:f=>{interval=f;return 1;},clearInterval:()=>{interval=null;}});
 return {window,calls,s,init:async()=>{await initial[0]();},tick:async()=>{if(interval)await interval();},keydown:e=>docCallbacks.keydown(e)};
}
test('automatic startup respects permission, legacy opt-out, recovery, cancel and one-shot Stop semantics',async()=>{
 for(const config of [{enabled:false},{permission:'denied'},{permission:'not-determined'},{recovery:'available'},{recovery:'staged'}]){const h=harness(config);await h.init();for(let i=0;i<10;i++)await h.tick();assert.equal(h.calls.includes('start'),false);}
 const cancelled=harness();await cancelled.init();cancelled.window.sessionSetup.cancel();for(let i=0;i<10;i++)await cancelled.tick();assert.equal(cancelled.calls.includes('start'),false);
 const h=harness();await h.init();for(let i=0;i<12;i++)await h.tick();assert.deepEqual(h.calls,['prepare','start']);for(let i=0;i<10;i++)await h.tick();assert.equal(h.calls.filter(c=>c==='start').length,1);
});
test('panic binding matches exact modifiers, ignores repeat and text editing',()=>{
 const h=harness();let prevented=false;const e={key:'p',ctrlKey:true,altKey:false,metaKey:false,shiftKey:true,repeat:false,isComposing:false,defaultPrevented:false,target:{closest:()=>null},preventDefault:()=>{prevented=true;}};
 h.keydown(e);assert.equal(prevented,true);assert.deepEqual(h.calls,['panic']);h.keydown({...e,repeat:true});h.keydown({...e,target:{closest:()=>({})}});h.s.connection='stale';h.keydown(e);assert.deepEqual(h.calls,['panic']);
});
