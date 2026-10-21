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
