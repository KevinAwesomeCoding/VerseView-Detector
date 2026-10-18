'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
test('connection notice never describes a stale or closed managed feed as connected',()=>{
  const window={},document={getElementById:()=>({addEventListener:()=>{}}),addEventListener:()=>{}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../src/observer.js'),'utf8'),{window,document,Event,setTimeout:()=>{}});
  const snapshot={connection:'connected',session:{host:{managed:true},control:{state:'stopped'}}};
  const notice=()=>window.observerView.connectionNotice(snapshot);
  assert.match(notice(),/Bundled backend connected/);
  for(const connection of ['stale','disconnected']){
    snapshot.connection=connection;assert.match(notice(),/feed unavailable/);assert.doesNotMatch(notice(),/backend connected/);
  }
  snapshot.connection='connected';snapshot.session.control.state='closed';assert.match(notice(),/controls are disabled/);
  snapshot.session.host.managed=false;assert.match(notice(),/explicit opt-in/);
  delete snapshot.session;assert.match(notice(),/explicit opt-in/);
});
test('Settings view acknowledges bot commands without visiting the engine controls or waiting for a timeout',async()=>{
  const listeners={},id='c'.repeat(32),sessionId='a'.repeat(32),hostId='b'.repeat(32);
  const snapshot={connection:'connected',message:'Connected',sources:[],session:{session_id:sessionId,pid:123,engine_state:'configured',config:{},
    control:{id:hostId,state:'stopped',actions:['start_bot'],results:[],bot:{status:'stopped',configured:true,message:'Stopped',events:[]}}}};
  const root={addEventListener:(name,fn)=>(listeners[name]??=[]).push(fn),dispatchEvent:()=>{}};
  const button={disabled:false,dataset:{engineAction:'start_bot',engineSession:sessionId}};
  const document={getElementById:()=>root,addEventListener:()=>{},querySelectorAll:selector=>selector.includes('start_bot')?[button]:[]};
  const window={previewShell:{getObserver:()=>snapshot,getBackend:()=>({status:'unavailable'}),getMode:()=> 'observer'},
    detectorSettings:{render:()=>''},verseviewDesktop:{botControl:async()=>({id,action:'start_bot',outcome:'submitted'})}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../src/observer.js'),'utf8'),{window,document,Event,setTimeout:()=>{}});
  await listeners.click[0]({target:{closest:()=>button}});
  snapshot.session.control.results=[{id,action:'start_bot',outcome:'requested',reason:'Bot request acknowledged'}];
  snapshot.session.control.actions=['stop_bot'];snapshot.session.control.bot.status='online';button.dataset.engineAction='stop_bot';
  window.observerView.updateRecoveryAvailability(snapshot);assert.equal(button.disabled,false);
  const html=window.observerView.settings(snapshot);
  assert.match(html,/Bot request acknowledged/);
  assert.doesNotMatch(html.match(/<button[^>]*data-engine-action="stop_bot"[^>]*>/)[0],/disabled/);
});

test('setup instructions distinguish the bundled host from an external detector and label saved Bible settings',()=>{
  const snapshot={connection:'connected',message:'Connected',sources:[],session:{session_id:'a'.repeat(32),pid:123,engine_state:'configured',config:{},
    host:{managed:true},control:{results:[],settings:{values:{bible_translation:'WEB'}}}}};
  const window={previewShell:{getObserver:()=>snapshot,getBackend:()=>({status:'unavailable'})},detectorSettings:{render:()=>''}};
  const document={getElementById:()=>({addEventListener:()=>{}}),addEventListener:()=>{}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../src/observer.js'),'utf8'),{window,document,Event,setTimeout:()=>{}});
  let html=window.observerView.settings(snapshot);
  assert.match(html,/Close the backend before editing credentials/);
  assert.match(html,/Saved Bible translation: WEB · applies on Start/);
  assert.doesNotMatch(html,/VERSEVIEW_OBSERVER|VERSEVIEW_DESKTOP_CONTROL/);
  snapshot.session.config.bible_translation='KJV';
  html=window.observerView.settings(snapshot);assert.match(html,/Engine Bible translation: KJV/);assert.doesNotMatch(html,/Saved Bible translation/);
  snapshot.session.host.managed=false;
  html=window.observerView.settings(snapshot);assert.match(html,/VERSEVIEW_OBSERVER=1/);assert.match(html,/VERSEVIEW_DESKTOP_CONTROL=1/);
});
