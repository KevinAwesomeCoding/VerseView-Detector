'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {EngineFeedReader}=require('../engine-feed.cjs');
function fixture(t){const directory=fs.mkdtempSync(path.join(os.tmpdir(),'vv-history-'));t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));const reader=new EngineFeedReader({directory}),id='a'.repeat(32);reader.snapshot.session={session_id:id,history_available:true};return{reader,id,file:path.join(directory,`transcript-${id}.jsonl`)};}
const row=i=>({id:i.toString(16).padStart(32,'0'),stream:i%2?'secondary':'primary',timestamp:new Date(1700000000000+i).toISOString(),is_final:true,text:'Speech '+i+' '+('a'.repeat(12000)),language:'en'});
test('bounded pages recover beginning and end beyond the recent 48 rows after reader reload',async t=>{
 const f=fixture(t);fs.writeFileSync(f.file,Array.from({length:100},(_,i)=>JSON.stringify(row(i))).join('\n')+'\n');
 let offset=0,rows=[],page;
 do{page=await f.reader.transcriptPage(f.id,offset);assert.ok(page.next>offset);offset=page.next;rows.push(...page.rows);}while(!page.complete);
 assert.equal(rows.length,100);assert.ok(rows[0].text.startsWith('Speech 0 '));assert.ok(rows[99].text.startsWith('Speech 99 '));
 const second=new EngineFeedReader({directory:f.reader.directory});second.snapshot=f.reader.snapshot;assert.equal((await second.transcriptPage(f.id,0)).rows[0].id,row(0).id);
 const current=await f.reader.transcriptPage(f.id,offset);assert.equal(current.rows.length,0);
 fs.appendFileSync(f.file,JSON.stringify({...row(100),text:'മലയാളം'})+'\n');assert.equal((await f.reader.transcriptPage(f.id,offset)).rows[0].text,'മലയാളം');
});
test('history cannot select arbitrary paths, another session, symlinks or malformed records',async t=>{
 const f=fixture(t);
 for(const[id,offset]of[['../secret',0],['b'.repeat(32),0],[f.id,-1],[f.id,1.5]])await assert.rejects(f.reader.transcriptPage(id,offset));
 fs.writeFileSync(f.file,'{"id":"not-allowed"}\n');await assert.rejects(f.reader.transcriptPage(f.id));
 if(process.platform!=='win32'){fs.unlinkSync(f.file);fs.symlinkSync('/etc/passwd',f.file);await assert.rejects(f.reader.transcriptPage(f.id));}
});
test('partially appended tail waits for next update, while legacy sessions report unavailable',async t=>{
 const f=fixture(t);fs.writeFileSync(f.file,JSON.stringify(row(0))+'\n'+JSON.stringify(row(1)).slice(0,40));
 const page=await f.reader.transcriptPage(f.id);assert.equal(page.rows.length,1);assert.equal(page.pending,true);
 f.reader.snapshot.session.history_available=false;assert.equal((await f.reader.transcriptPage(f.id)).available,false);
});
