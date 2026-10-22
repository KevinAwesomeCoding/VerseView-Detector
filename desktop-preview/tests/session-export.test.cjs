'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {exportSession}=require('../session-export.cjs');
function fixture(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'vv-export-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const sessionId='a'.repeat(32),exportId='b'.repeat(32),sourceId='c'.repeat(32),data=Buffer.from('Original beginning\n'+'മലയാളം '.repeat(800)+'\nOriginal end');
 fs.mkdirSync(path.join(root,'Exports'));fs.writeFileSync(path.join(root,'Exports',exportId+'.txt'),data);
 const packet={id:exportId,kind:'transcript',source_id:sourceId,name:'VerseView-transcript.txt',sha256:crypto.createHash('sha256').update(data).digest('hex')};
 const snapshot={connection:'connected',session:{session_id:sessionId,pid:123,host:{managed:true},control:{notes:{export:packet}}}};
 return {root,packet,snapshot,data,sessionId,exportId,reader:{poll:async()=>snapshot},manager:{profile:root,state:{status:'ready',owned:true,pid:123}}};
}
test('native export saves the exact full Unicode packet and returns its chosen path',async t=>{
 const f=fixture(t),destination=path.join(f.root,'chosen.txt');
 const result=await exportSession({...f,chooseDestination:async options=>{assert.equal(options.defaultPath,'VerseView-transcript.txt');return {filePath:destination};}});
 assert.equal(result.status,'saved');assert.equal(result.path,destination);assert.deepEqual(fs.readFileSync(destination),f.data);
});
test('cancel, stale session, unowned backend, tampered bytes and symlinks never write a destination',async t=>{
 const f=fixture(t),destination=path.join(f.root,'existing.txt');fs.writeFileSync(destination,'KEEP');
 let calls=0;const chooseDestination=async()=>{calls++;return {filePath:destination};};
 const cancelled=await exportSession({...f,chooseDestination:async()=>({canceled:true})});assert.equal(cancelled.status,'cancelled');
 for(const modify of [()=>f.snapshot.connection='stale',()=>f.manager.state.owned=false,()=>f.snapshot.session.pid=999]){
  const saved=structuredClone(f.snapshot),manager={...f.manager.state};modify();await assert.rejects(exportSession({...f,chooseDestination}));Object.assign(f.snapshot,saved);Object.assign(f.manager.state,manager);
 }
 fs.writeFileSync(path.join(f.root,'Exports',f.exportId+'.txt'),'CHANGED');await assert.rejects(exportSession({...f,chooseDestination}));
 assert.equal(fs.readFileSync(destination,'utf8'),'KEEP');assert.equal(calls,0);
});
test('a session change while Save dialog is open cannot export into another session',async t=>{
 const f=fixture(t),destination=path.join(f.root,'never.txt');
 await assert.rejects(exportSession({...f,chooseDestination:async()=>{f.snapshot.session.session_id='d'.repeat(32);return {filePath:destination};}}));
 assert.equal(fs.existsSync(destination),false);
});
