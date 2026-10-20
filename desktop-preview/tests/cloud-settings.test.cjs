'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const cloud=require('../src/cloud-policy.js'),settings=require('../src/settings-policy.js');
const view={enabled:true,routes:Object.fromEntries(Object.entries(cloud.routes).map(([k,a])=>[k,a[0]])),watcher_min_gap:20,
  limits:cloud.ceilings,confirmed:['groq','cloudflare','gemini'],sync_url:'',credentials:{groq_api_key:true,gemini_api_key:'SECRET',unexpected:'SECRET'}};
test('cloud metadata decoder never exports credential values or arbitrary fields',()=>{
 const decoded=cloud.decode({...view,private_key:'SECRET'});
 assert.equal(decoded.credentials.groq_api_key,true);assert.equal(decoded.credentials.gemini_api_key,false);
 assert.equal(JSON.stringify(decoded).includes('SECRET'),false);
});
test('cloud patch boundary allows only reviewed models, lower budgets and bounded write-only credentials',()=>{
 assert.deepEqual(settings.validatePatch({cloud_settings:{credentials:{groq_api_key:'PRIVATE'}}}),{cloud_settings:{credentials:{groq_api_key:'PRIVATE'}}});
 for(const patch of [{routes:{summary:'gemini|paid'}},{credentials:{evil:'PRIVATE'}},{credentials:{groq_api_key:'BAD\nPRIVATE'}},
  {limits:{...cloud.ceilings,groq:{rpd:1001,tpd:200000}}},{watcher_min_gap:0},{unknown:true}])assert.throws(()=>cloud.validate(patch));
});
test('Drive URL boundary excludes other hosts, embedded passwords and extra query fields',()=>{
 assert.equal(cloud.syncURL('https://drive.google.com/uc?export=download&id=abcdefghijk'),true);
 for(const url of ['http://drive.google.com/uc?export=download&id=abcdefghijk','https://user:secret@drive.google.com/uc?export=download&id=abcdefghijk',
 'https://drive.google.com/uc?export=download&id=abcdefghijk&token=secret','https://other.example/?token=secret'])assert.equal(cloud.syncURL(url),false);
});
