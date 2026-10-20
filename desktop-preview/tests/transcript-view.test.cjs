'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
test('Live view toggle loads full history, preserves stream separation, and does not start or stop the engine',async()=>{
 const listeners={},store={},calls=[],s={session_id:'a'.repeat(32),revision:1,history_available:true,transcripts:[]};
 let view;
 const root={querySelector:()=>({}),querySelectorAll:()=>[],addEventListener:(n,f)=>(listeners[n]??=[]).push(f),dispatchEvent:e=>{for(const f of listeners[e.type]||[])f(e);}};
 const window={previewShell:{getObserver:()=>({session:s})},verseviewDesktop:{transcriptPage:async(id,offset)=>{calls.push([id,offset]);return{available:true,rows:[{id:'1',stream:'primary',timestamp:'2026-10-20T00:00:00Z',text:'First speech',is_final:true},{id:'2',stream:'secondary',timestamp:'2026-10-20T00:00:01Z',text:'മലയാളം',is_final:true}],next:100,complete:true};}}};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../src/transcript-view.js'),'utf8'),{window,document:{getElementById:()=>root},localStorage:{getItem:k=>store[k],setItem:(k,v)=>store[k]=v},Event:class{constructor(type){this.type=type;}}});
 view=window.transcriptView;assert.equal(view.isFull(),false);assert.equal(view.rows(null,'primary').length,0);
 const click=value=>listeners.click[0]({target:{closest:selector=>selector==='[data-transcript-view]'?{dataset:{transcriptView:value}}:null}});
 click('full');await new Promise(setImmediate);assert.equal(view.isFull(),true);assert.equal(calls.length,1);
 assert.equal(view.rows(s,'primary')[0].text,'First speech');assert.equal(view.rows(s,'secondary')[0].text,'മലയാളം');
 root.dispatchEvent({type:'preview:observer'});await new Promise(setImmediate);assert.equal(calls.length,1,'Caught-up pages must not continuously fetch themselves');
 click('focus');assert.equal(view.isFull(),false);assert.equal(store['verseview.live-transcript-view'],'focus');
 assert.equal(calls.length,1);assert.match(view.controls(s),/Full transcript/);
});
test('transcript scroll preserves reading position, follows the bottom, and Jump to live restores following',()=>{
 const listeners={};let boxes=[{dataset:{fullTranscript:'primary'},scrollTop:120,scrollHeight:1000,clientHeight:200},{dataset:{fullTranscript:'secondary'},scrollTop:800,scrollHeight:1000,clientHeight:200}];
 const root={querySelectorAll:()=>boxes,addEventListener:(n,f)=>listeners[n]=f};const window={};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../src/transcript-view.js'),'utf8'),{window,document:{getElementById:()=>root},localStorage:{getItem:()=>null}});
 const saved=window.transcriptView.beforePatch();boxes=boxes.map(e=>({...e,scrollTop:0,scrollHeight:1200}));window.transcriptView.afterPatch(saved);
 assert.equal(boxes[0].scrollTop,120);assert.equal(boxes[1].scrollTop,1200);
 listeners.click({target:{closest:s=>s==='[data-transcript-jump]'?{}:null}});assert.equal(boxes[0].scrollTop,1200);assert.equal(boxes[0].dataset.follow,'true');
});
