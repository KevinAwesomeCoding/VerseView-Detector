'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {EngineCommands}=require('../engine-commands.cjs');
const {decodeSnapshot}=require('../engine-feed.cjs');
test('verse commands are bounded, session-bound and carry no arbitrary fields or retry',async t=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'vv-verse-command-'));t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
 const id='a'.repeat(32),revision='c'.repeat(32),now=Date.now(),control={id:'b'.repeat(32),state:'running',actions:['set_context','verse_preview','chapter_browse','send_reference']};
 const s={connection:'connected',session:{session_id:id,pid:123,updated_at:new Date(now).toISOString(),control}};
 const inbox=path.join(directory,`control-123-${control.id}`);fs.mkdirSync(inbox);
 const commands=new EngineCommands({directory,poll:async()=>s},{clock:()=>now});
 const submit=(action,value)=>commands.submit(id,action,undefined,undefined,undefined,undefined,undefined,value);
 for(const [a,v] of [['set_context',{reference:'John 3',context_revision:revision}],['verse_preview',{reference:'John 3:16'}],['chapter_browse',{reference:'John 3',page:1}],['send_reference',{selection_id:revision}]]){
  const result=await submit(a,v),request=JSON.parse(fs.readFileSync(path.join(inbox,`command-${result.id}.json`)));
  assert.equal(result.outcome,'submitted');for(const [k,x]of Object.entries(v))assert.equal(request[k],x);
 }
 for(const [a,v] of [['verse_preview',{reference:'x'.repeat(129)}],['verse_preview',{reference:'John 3:16',path:'/tmp/key'}],['send_reference',{selection_id:'../x'}],['set_context',{reference:'John 3'}],['chapter_browse',{reference:'John 3',page:25}]])await assert.rejects(submit(a,v));
 control.actions=[];await assert.rejects(submit('send_reference',{selection_id:revision}));assert.equal(fs.readdirSync(inbox).length,4);
});
test('verse feed projects only bounded preview data and keeps exact translation and stale status',()=>{
 const now=Date.now(),id='a'.repeat(32),v={context:{revision:id,book:'John',chapter:'3',verse:'16'},books:[{name:'John',chapters:21}],translation:'mal',selected:{id,reference:'John 3:16',text:'യോഹന്നാൻ'.repeat(2000),translation:'mal',status:'stale',secret:'private'},history:Array(200).fill({reference:'John 3:16',time:'10:00',secret:'private'}),chapter:{reference:'John 3',page:100,rows:Array(20).fill({reference:'John 3:16',text:'Verse'}),status:'ready'},last_send:{candidate_id:id,reference:'John 3:16',outcome:'SUPPRESSED',reason:'Worship on'}};
 const decoded=decodeSnapshot({schema:1,pid:123,session_id:id,revision:1,origin:'engine',started_at:new Date(now).toISOString(),updated_at:new Date(now).toISOString(),engine_state:'running',transcripts:[],delivery_events:[],config:{streams:{primary:{enabled:true},secondary:{enabled:false}}},control:{id,state:'running',actions:['send_reference'],verses:v}},now).control.verses;
 assert.equal(decoded.selected.status,'stale');assert.equal(decoded.selected.translation,'mal');assert.equal(decoded.selected.text.length,6000);
 assert.equal(decoded.history.length,128);assert.equal(decoded.chapter.rows.length,8);assert.equal(decoded.chapter.page,24);assert.equal(JSON.stringify(decoded).includes('private'),false);
});

test('Display accepts only the current suppressed candidate and exact reference',async t=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'vv-suppressed-command-'));t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
 const id='a'.repeat(32),candidate='c'.repeat(12),now=Date.now(),control={id:'b'.repeat(32),state:'running',actions:['display_suppressed']};
 const events=[{candidate_id:candidate,reference:'John 10:12',outcome:'SUPPRESSED'}];
 const snapshot={connection:'connected',session:{session_id:id,pid:123,updated_at:new Date(now).toISOString(),control,delivery_events:events}};
 const inbox=path.join(directory,`control-123-${control.id}`);fs.mkdirSync(inbox);
 const commands=new EngineCommands({directory,poll:async()=>snapshot},{clock:()=>now});
 const send=value=>commands.submit(id,'display_suppressed',undefined,undefined,undefined,undefined,undefined,value);
 const result=await send({candidate_id:candidate,reference:'John 10:12'});
 assert.equal(JSON.parse(fs.readFileSync(path.join(inbox,`command-${result.id}.json`))).reference,'John 10:12');
 await assert.rejects(send({candidate_id:candidate,reference:'John 10:11'}));
 await assert.rejects(send({candidate_id:'d'.repeat(12),reference:'John 10:12'}));
 events.push({candidate_id:candidate,reference:'John 10:12',outcome:'COMMAND_ACCEPTED'});
 await assert.rejects(send({candidate_id:candidate,reference:'John 10:12'}));
});

test('chapter grid and inbox review commands keep exact typed identities and reject extra fields',async t=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'vv-review-command-'));t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
 const id='a'.repeat(32),revision='c'.repeat(32),now=Date.now(),control={id:'b'.repeat(32),state:'running',actions:['grid_preview','clear_history','preview_suggestion','dismiss_suggestion','clear_suggestions']};
 const snapshot={connection:'connected',session:{session_id:id,pid:123,updated_at:new Date(now).toISOString(),control}};
 const inbox=path.join(directory,`control-123-${control.id}`);fs.mkdirSync(inbox);
 const commands=new EngineCommands({directory,poll:async()=>snapshot},{clock:()=>now});
 const submit=(a,v)=>commands.submit(id,a,undefined,undefined,undefined,undefined,undefined,v);
 for(const [action,value] of [['grid_preview',{reference:'John 3:36',context_revision:revision}],['clear_history',{history_revision:revision}],['preview_suggestion',{suggestion_id:revision}],['dismiss_suggestion',{suggestion_id:revision}],['clear_suggestions',{revision}]]){
  const result=await submit(action,value),request=JSON.parse(fs.readFileSync(path.join(inbox,`command-${result.id}.json`)));
  for(const [key,item] of Object.entries(value))assert.equal(request[key],item);
  await assert.rejects(submit(action,{...value,extra:'unsafe'}));
 }
 await assert.rejects(submit('grid_preview',{reference:'John 3:36'}));
 await assert.rejects(submit('dismiss_suggestion',{suggestion_id:'../x'}));
 snapshot.connection='stale';await assert.rejects(submit('clear_history',{history_revision:revision}));
 assert.equal(fs.readdirSync(inbox).length,5);
});

test('notes and memory requests are bounded opaque operations with no renderer paths or content',async t=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'vv-notes-commands-'));t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
 const id='a'.repeat(32),revision='c'.repeat(32),now=Date.now(),control={id:'b'.repeat(32),state:'stopped',actions:['generate_notes','cancel_notes','prepare_export','prepare_memory_clear','clear_memory']};
 const snapshot={connection:'connected',session:{session_id:id,pid:123,updated_at:new Date(now).toISOString(),control}};
 const inbox=path.join(directory,`control-123-${control.id}`);fs.mkdirSync(inbox);
 const client=new EngineCommands({directory,poll:async()=>snapshot},{clock:()=>now});
 const submit=(a,v)=>client.submit(id,a,undefined,undefined,undefined,undefined,undefined,v);
 for(const [action,value] of [['generate_notes',{revision}],['cancel_notes',{}],['prepare_export',{revision,kind:'all'}],['prepare_memory_clear',{}],['clear_memory',{revision}]]){
  await submit(action,value);await assert.rejects(submit(action,{...value,path:'/tmp/unsafe'}));
 }
 await assert.rejects(submit('generate_notes',{}));await assert.rejects(submit('prepare_export',{revision,kind:'credentials'}));
 control.actions=[];await assert.rejects(submit('clear_memory',{revision}));assert.equal(fs.readdirSync(inbox).length,5);
});
