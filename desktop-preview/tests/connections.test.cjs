'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {importProfile}=require('../profile-transfer.cjs'),policy=require('../src/settings-policy.js');
function fixture(t){const root=fs.mkdtempSync(path.join(os.tmpdir(),'vv-import-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));const id='a'.repeat(32),revision='b'.repeat(32),snapshot={connection:'connected',session:{session_id:id,pid:123,host:{managed:true},control:{state:'stopped',settings:{revision},actions:['save_settings']}}};const file=path.join(root,'selected.json');fs.writeFileSync(file,JSON.stringify({type:'service_account',private_key:'PRIVATE-QA'}));const calls=[];return {root,file,id,revision,snapshot,calls,reader:{poll:async()=>snapshot},manager:{profile:root,state:{status:'ready',owned:true,pid:123}},commands:{submit:async(...args)=>{calls.push(args);return {id:'c'.repeat(32)};}}};}
test('native import stages only a bounded private packet and sends an opaque command',async t=>{
 const f=fixture(t);await importProfile({...f,sessionId:f.id,kind:'gcp',includeCredentials:true,chooseFile:async()=>({filePaths:[f.file]})});
 const args=f.calls[0],payload=args.at(-1);assert.equal(args[1],'connection_action');assert.equal(payload.operation,'import');assert.equal(JSON.stringify(args).includes('PRIVATE-QA'),false);assert.match(payload.attachment_id,/^[a-f0-9]{32}$/);
 assert.equal(JSON.parse(fs.readFileSync(path.join(f.root,'Imports',payload.attachment_id+'.json'))).kind,'gcp');
});
test('import cancel, stale revision, denied scope and changed session never submit',async t=>{
 const f=fixture(t);const base={...f,sessionId:f.id,kind:'gcp',includeCredentials:true};
 await importProfile({...base,chooseFile:async()=>({canceled:true})});assert.equal(f.calls.length,0);
 await assert.rejects(importProfile({...base,includeCredentials:false,chooseFile:async()=>({filePaths:[f.file]})}));
 await assert.rejects(importProfile({...base,revision:'d'.repeat(32),chooseFile:async()=>({filePaths:[f.file]})}));
 await assert.rejects(importProfile({...base,chooseFile:async()=>{f.snapshot.session.session_id='e'.repeat(32);return {filePaths:[f.file]};}}));assert.equal(f.calls.length,0);
});
test('developer options and connection credentials remain typed; URLs cannot smuggle credentials',()=>{
 assert.doesNotThrow(()=>policy.validatePatch({local_llm_endpoint:'http://127.0.0.1:11434',local_llm_role_verse:'local',chunk:4096,rate:16000}));
 assert.doesNotThrow(()=>policy.validatePatch({connection_secrets:{local_llm_auth_token:'test',local_llm_extra_headers:'{"X-Key":"test"}'}}));
 for(const v of [{local_llm_endpoint:'http://user:secret@host/'},{chunk:0},{rate:16001},{cooldown:0},{connection_secrets:{unknown:'private'}},{connection_secrets:{local_llm_extra_headers:'[]'}}])assert.throws(()=>policy.validatePatch(v));
});
test('connection snapshots expose presence and bounded target/review metadata, never private packets',()=>{
 const {decodeSnapshot}=require('../engine-feed.cjs');const now=new Date().toISOString();
 const fixture={schema:1,revision:1,origin:'engine',pid:123,session_id:'a'.repeat(32),started_at:now,updated_at:now,config:{streams:{primary:{enabled:true},secondary:{enabled:false}}},transcripts:[],delivery_events:[],control:{id:'b'.repeat(32),state:'stopped',actions:['connection_action'],pending:[],results:[],connections:{status:'idle',credentials:{local_llm_auth_token:true,private:'SECRET'},raw:'SECRET',local_targets:{verse:{endpoint:'http://127.0.0.1:11434',model:'qa:model',token:'SECRET'}},export:{id:'c'.repeat(32),source_id:'d'.repeat(32),sha256:'e'.repeat(64),include_credentials:true,contents:'SECRET'},atem_review:{id:'f'.repeat(32),target:'192.0.2.1',settings_revision:'d'.repeat(32),expires:999,private:'SECRET'}}}};
 const v=decodeSnapshot(fixture).control.connections;assert.equal(v.credentials.local_llm_auth_token,true);assert.equal(v.export.include_credentials,true);assert.equal(v.atem_review.expires,undefined);assert.equal(JSON.stringify(v).includes('SECRET'),false);
});
