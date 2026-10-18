'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
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
