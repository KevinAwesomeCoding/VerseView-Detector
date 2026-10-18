'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),{EventEmitter}=require('node:events');
const {OutlineOutput}=require('../outline-output.cjs');
function setup(){
  const windows=[];
  class FakeWindow extends EventEmitter{
    constructor(options){super();this.options=options;this.webContents=new EventEmitter();this.messages=[];
      this.webContents.send=(channel,value)=>this.messages.push({channel,value});
      this.webContents.setWindowOpenHandler=handler=>{this.popup=handler;};windows.push(this);}
    isDestroyed(){return !!this.destroyed;}
    close(){this.destroyed=true;this.emit('closed');}
    loadFile(file){this.file=file;return Promise.resolve();}
    setFullScreen(value){this.fullscreen=value;}
    show(){this.shown=true;}
  }
  const displays=[{id:1,label:'Primary',bounds:{x:0,y:0,width:1470,height:956},workArea:{x:0,y:24,width:1470,height:900}},
    {id:2,label:'Left projector',bounds:{x:-1920,y:0,width:1920,height:1080}}];
  const snapshot={connection:'connected',session:{session_id:'a'.repeat(32),updated_at:new Date().toISOString(),
    control:{id:'b'.repeat(32),outline:{revision:'c'.repeat(32),text:'<script>plain notes</script>'}}}};
  const screen={getAllDisplays:()=>displays,getPrimaryDisplay:()=>displays[0]};
  const changes=[],manager=new OutlineOutput({BrowserWindow:FakeWindow,screen,readSnapshot:async()=>snapshot,
    page:'/fixed/outline-display.html',preload:'/fixed/outline-preload.cjs',onChange:value=>changes.push(value)});
  return {windows,displays,snapshot,screen,changes,manager};
}
test('outline output never opens automatically, uses exact native bounds, and closes with Escape',async()=>{
  const f=setup();f.manager.update(f.snapshot);assert.equal(f.windows.length,0);
  await f.manager.open(f.snapshot.session.session_id,'2');const output=f.windows[0];
  assert.equal(output.options.x,-1920);assert.equal(output.options.width,1920);assert.equal(output.options.show,false);
  assert.deepEqual(output.options.webPreferences,{preload:'/fixed/outline-preload.cjs',nodeIntegration:false,
    contextIsolation:true,sandbox:true,webSecurity:true,spellcheck:false,devTools:false});
  output.emit('ready-to-show');assert.equal(output.fullscreen,true);assert.equal(output.shown,true);
  output.webContents.emit('did-finish-load');await new Promise(resolve=>setImmediate(resolve));
  assert.equal(output.messages[0].value.text,'<script>plain notes</script>');
  assert.deepEqual(output.popup(),{action:'deny'});
  output.webContents.emit('before-input-event',{}, {key:'Escape'});assert.equal(f.manager.state().open,false);
});
test('stale/unknown sessions and missing targets cannot open or silently fall back',async()=>{
  const f=setup(),session=f.snapshot.session.session_id;
  await assert.rejects(f.manager.open(session,'999'));await assert.rejects(f.manager.open('d'.repeat(32),'1'));
  await assert.rejects(f.manager.open(session,'../../settings.json'));
  f.snapshot.session.updated_at=new Date(Date.now()-10000).toISOString();await assert.rejects(f.manager.open(session,'1'));
  assert.equal(f.windows.length,0);
});
test('windowed routing, latest-on-load text, session changes and removed displays are explicit',async()=>{
  const f=setup(),session=f.snapshot.session.session_id;
  await f.manager.open(session,'windowed');let output=f.windows[0];output.emit('ready-to-show');
  assert.equal(output.options.x,0);assert.equal(output.options.y,24);assert.equal(output.options.width,800);assert.equal(output.fullscreen,undefined);
  f.snapshot.session.control.outline={revision:'d'.repeat(32),text:'Latest notes before load'};
  output.webContents.emit('did-finish-load');await new Promise(resolve=>setImmediate(resolve));
  assert.equal(output.messages.at(-1).value.text,'Latest notes before load');
  f.snapshot.session.session_id='e'.repeat(32);f.manager.update(f.snapshot);assert.equal(f.manager.state().open,false);
  await f.manager.open(f.snapshot.session.session_id,'2');output=f.windows[1];
  f.displays.pop();f.manager.update(f.snapshot);assert.equal(output.destroyed,true);
  assert.match(f.manager.state().message,/disconnected/);
});
test('a lost feed closes only the owned output and never starts another window',async()=>{
  const f=setup();await f.manager.open(f.snapshot.session.session_id,'windowed');
  f.snapshot.connection='stale';f.manager.update(f.snapshot);
  assert.equal(f.manager.state().open,false);assert.equal(f.windows.length,1);
  assert.match(f.manager.state().message,/feed/);
});
