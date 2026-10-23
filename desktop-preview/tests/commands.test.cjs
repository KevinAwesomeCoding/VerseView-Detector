'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { EngineCommands } = require('../engine-commands.cjs');
const { EngineFeedReader, decodeSnapshot } = require('../engine-feed.cjs');
// Match ObserverPublisher's atomic replacement, including on coarse-timestamp filesystems.
function publishFixture(file, value) {
  const temporary = file + '.next';
  fs.writeFileSync(temporary, JSON.stringify(value));
  fs.renameSync(temporary, file);
}
function setup(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'vv-command-test-'));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const now = Date.now(), sessionId = 'a'.repeat(32), controlId = 'b'.repeat(32);
  const session = { pid: 123, session_id: sessionId, updated_at: new Date(now).toISOString(),
    control: { id: controlId, state: 'stopped', actions: ['start'], pending: [], results: [] } };
  const snapshot = { connection: 'connected', session };
  const reader = { directory, poll: async () => snapshot };
  const inbox = path.join(directory, `control-123-${controlId}`);
  fs.mkdirSync(inbox);
  return { now, directory, sessionId, controlId, session, snapshot, reader, inbox,
    client: new EngineCommands(reader, { clock: () => now }) };
}
test('start writes one bounded request with exact session/control identity, never a success claim', async t => {
  const f = setup(t);
  const result = await f.client.submit(f.sessionId, 'start');
  assert.equal(result.outcome, 'submitted');
  const files = fs.readdirSync(f.inbox);
  assert.deepEqual(files, [`command-${result.id}.json`]);
  const request = JSON.parse(fs.readFileSync(path.join(f.inbox, files[0])));
  assert.equal(request.session_id, f.sessionId);
  assert.equal(request.control_id, f.controlId);
  assert.equal(request.created_at, f.now / 1000);
  assert.equal(f.reader.commandTransition.id, result.id);
});
test('new session requires a stopped detector and writes no extra fields', async t => {
  const f = setup(t);
  f.session.control.actions = ['new_session'];
  const result = await f.client.submit(f.sessionId, 'new_session', undefined, undefined, undefined, undefined, undefined, {});
  const request = JSON.parse(fs.readFileSync(path.join(f.inbox, `command-${result.id}.json`)));
  assert.equal(request.action, 'new_session');
  assert.equal(Object.hasOwn(request, 'recovery_revision'), false);
  await assert.rejects(f.client.submit(f.sessionId, 'new_session', undefined, undefined, undefined, undefined, undefined, { record_id: 'a'.repeat(32) }));
  f.session.control.state = 'running'; f.session.control.actions = [];
  await assert.rejects(f.client.submit(f.sessionId, 'new_session'));
});
test('stale, ambiguous, wrong-session and read-only sources cannot receive commands', async t => {
  const f = setup(t);
  for (const state of ['stale', 'ambiguous', 'unavailable']) {
    f.snapshot.connection = state;
    await assert.rejects(f.client.submit(f.sessionId, 'start'));
  }
  f.snapshot.connection = 'connected';
  await assert.rejects(f.client.submit('c'.repeat(32), 'start'));
  f.session.control = null;
  await assert.rejects(f.client.submit(f.sessionId, 'start'));
  assert.equal(fs.readdirSync(f.inbox).length, 0);
});
test('only an actual pending candidate can be answered; arbitrary actions and paths are rejected', async t => {
  const f = setup(t);
  f.session.control.state = 'running';
  f.session.control.pending = [{ candidate_id: 'candidate-1' }];
  await assert.rejects(f.client.submit(f.sessionId, 'approve', 'missing'));
  await assert.rejects(f.client.submit(f.sessionId, 'goto', '../../settings.json'));
  await assert.rejects(f.client.submit('../../settings.json', 'start'));
  const result = await f.client.submit(f.sessionId, 'approve', 'candidate-1');
  const request = JSON.parse(fs.readFileSync(path.join(f.inbox, `command-${result.id}.json`)));
  assert.equal(request.candidate_id, 'candidate-1');
  assert.equal(request.action, 'approve');
});
test('missing inbox fails without retry or creating a new backend', async t => {
  const f = setup(t);
  fs.rmdirSync(f.inbox);
  await assert.rejects(f.client.submit(f.sessionId, 'start'));
  assert.equal(fs.readdirSync(f.directory).length, 0);
});
test('recovery decisions carry only an exact revision and never start recognition', async t => {
  const f = setup(t), revision = 'd'.repeat(32);
  f.session.control.actions = ['restore_session', 'discard_session'];
  f.session.control.recovery = { status: 'available', revision };
  await assert.rejects(f.client.submit(f.sessionId, 'restore_session', undefined, undefined, 'e'.repeat(32)));
  const result = await f.client.submit(f.sessionId, 'restore_session', undefined, undefined, revision);
  const request = JSON.parse(fs.readFileSync(path.join(f.inbox, `command-${result.id}.json`)));
  assert.equal(request.recovery_revision, revision);
  assert.equal(request.action, 'restore_session');
  assert.equal(f.reader.commandTransition, undefined);
  f.session.control.state = 'running';
  await assert.rejects(f.client.submit(f.sessionId, 'discard_session', undefined, undefined, revision));
});
test('explicit process selection follows only our acknowledged start across session rotation', async t => {
  const f = setup(t), reader = new EngineFeedReader({ directory: f.directory, clock: () => f.now });
  const fixture = { ...f.session, schema: 1, revision: 1, origin: 'engine', started_at: new Date(f.now).toISOString(),
    engine_state: 'configured', config: { streams: { primary: { enabled: true }, secondary: { enabled: false } } },
    transcripts: [], delivery_events: [] };
  const file = path.join(f.directory, 'engine-123.json');
  publishFixture(file, fixture);
  await reader.poll(); await reader.select(f.sessionId);
  const client = new EngineCommands(reader, { clock: () => f.now });
  const result = await client.submit(f.sessionId, 'start');
  fixture.session_id = 'c'.repeat(32);
  fixture.control.results = [{ id: result.id, action: 'start', outcome: 'requested' }];
  publishFixture(file, fixture);
  assert.equal((await reader.poll()).selected, fixture.session_id);
  assert.equal(reader.snapshot.connection, 'connected');
  fixture.session_id = 'd'.repeat(32); fixture.control.results = [];
  publishFixture(file, fixture);
  assert.equal((await reader.poll()).connection, 'unavailable');
});
test('Clear Memory follows only its exact acknowledged rotation and stays stopped', async t => {
  const f = setup(t), reader = new EngineFeedReader({ directory: f.directory, clock: () => f.now });
  const fixture = { ...f.session, schema: 1, revision: 1, origin: 'engine', started_at: new Date(f.now).toISOString(),
    engine_state: 'stopped', config: { streams: { primary: { enabled: true }, secondary: { enabled: false } } },
    transcripts: [], delivery_events: [] };
  fixture.control.actions = ['clear_memory'];
  const file = path.join(f.directory, 'engine-123.json');
  publishFixture(file, fixture);
  await reader.poll(); await reader.select(f.sessionId);
  const client = new EngineCommands(reader, { clock: () => f.now });
  const result = await client.submit(f.sessionId, 'clear_memory', undefined, undefined, undefined, undefined, undefined, { revision: 'e'.repeat(32) });
  fixture.session_id = 'c'.repeat(32); fixture.revision++;
  fixture.control.results = [{ id: 'f'.repeat(32), action: 'clear_memory', outcome: 'requested' }];
  publishFixture(file, fixture);
  fs.utimesSync(file, 1700000000, 1700000000);
  assert.equal((await reader.poll()).connection, 'unavailable');
  fixture.revision++; fixture.control.results = [{ id: result.id, action: 'clear_memory', outcome: 'requested' }];
  publishFixture(file, fixture);
  fs.utimesSync(file, 1700000000, 1700000000);
  const cleared = await reader.poll();
  assert.equal(cleared.selected, fixture.session_id);
  assert.equal(cleared.connection, 'connected');
  assert.equal(cleared.session.control.state, 'stopped');
});
test('control decoder exposes only bounded typed fields', t => {
  const f = setup(t);
  const decoded = decodeSnapshot({ ...f.session, schema: 1, revision: 1, origin: 'engine',
    started_at: new Date(f.now).toISOString(), config: { streams: { primary: { enabled: true }, secondary: { enabled: false } } },
    transcripts: [], delivery_events: [], control: { ...f.session.control, secret: 'private', actions: ['start', 'goto'] } });
  assert.deepEqual(decoded.control.actions, ['start']);
  assert.equal(JSON.stringify(decoded).includes('private'), false);
});
test('selected owned backend follows only an acknowledged bot Start with the same process/control',async t=>{
  const f=setup(t),reader=new EngineFeedReader({directory:f.directory,clock:()=>f.now});
  const fixture={...f.session,schema:1,revision:1,origin:'engine',host:{managed:true},started_at:new Date(f.now).toISOString(),
    config:{streams:{primary:{enabled:true},secondary:{enabled:false}}},transcripts:[],delivery_events:[]};
  const file=path.join(f.directory,'engine-123.json');publishFixture(file, fixture);
  await reader.poll();await reader.select(f.sessionId);
  const id='e'.repeat(32);fixture.session_id='d'.repeat(32);fixture.revision++;
  fixture.control.results=[{id,action:'start',outcome:'requested'}];
  fixture.control.bot={status:'online',events:[]};
  publishFixture(file, fixture);assert.equal((await reader.poll()).connection,'unavailable');
  fixture.revision++;fixture.control.bot.events=[{id,route:'/start',http_status:200,timestamp:new Date(f.now).toISOString(),outcome:'acknowledged'}];
  publishFixture(file, fixture);assert.equal((await reader.poll()).selected,fixture.session_id);
  fixture.session_id='c'.repeat(32);fixture.revision++;fixture.control.bot.events=[];
  publishFixture(file, fixture);assert.equal((await reader.poll()).connection,'unavailable');
});
test('bot controls require a current explicit capability and never accept renderer credentials',async t=>{
  const f=setup(t);f.session.control.actions=['start_bot'];
  await assert.rejects(f.client.submit(f.sessionId,'stop_bot'));
  const result=await f.client.submit(f.sessionId,'start_bot');
  const request=JSON.parse(fs.readFileSync(path.join(f.inbox,`command-${result.id}.json`)));
  assert.deepEqual(Object.keys(request).sort(),['id','control_id','session_id','action','created_at'].sort());
  f.session.control.actions=[];await assert.rejects(f.client.submit(f.sessionId,'start_bot'));
});
test('bot decoder omits credentials and private log text and bounds command history',t=>{
  const f=setup(t),fixture={...f.session,schema:1,revision:1,origin:'engine',started_at:new Date(f.now).toISOString(),
    config:{streams:{primary:{enabled:true},secondary:{enabled:false}}},transcripts:[],delivery_events:[]};
  fixture.control.bot={status:'online',configured:true,pid:456,token:'SECRET',log:'SECRET',proof:{frozen:true,token:'SECRET'},
    events:Array.from({length:40},()=>({id:'c'.repeat(32),route:'/goto',timestamp:new Date(f.now).toISOString(),http_status:200,outcome:'acknowledged',ref:'SECRET'}))};
  fixture.control.bot.events[39].outcome='unknown';fixture.control.bot.events[39].http_status=504;
  const bot=decodeSnapshot(fixture).control.bot;
  assert.equal(bot.events.length,32);assert.equal(bot.pid,456);assert.equal(JSON.stringify(bot).includes('SECRET'),false);
  assert.equal(bot.events.at(-1).outcome,'unknown');
});
test('credential pulls require current capability and carry no renderer URL or credential data',async t=>{
  const f=setup(t);f.session.control.actions=['pull_settings'];
  const result=await f.client.submit(f.sessionId,'pull_settings');
  const request=JSON.parse(fs.readFileSync(path.join(f.inbox,`command-${result.id}.json`)));
  assert.deepEqual(Object.keys(request).sort(),['id','control_id','session_id','action','created_at'].sort());
  f.session.control.actions=[];await assert.rejects(f.client.submit(f.sessionId,'pull_settings'));
});
test('sync decoder exports bounded status without URLs, keys or downloaded payload',t=>{
  const f=setup(t),fixture={...f.session,schema:1,revision:1,origin:'engine',started_at:new Date(f.now).toISOString(),
    config:{streams:{primary:{enabled:true},secondary:{enabled:false}}},transcripts:[],delivery_events:[]};
  fixture.control.sync={status:'applied',configured:true,busy:false,updated_count:999,message:'Credentials updated.',
    url:'SECRET',credentials:{key:'SECRET'},raw_error:'SECRET',completed_at:new Date(f.now).toISOString()};
  const value=decodeSnapshot(fixture).control.sync;
  assert.equal(value.updated_count,13);assert.equal(JSON.stringify(value).includes('SECRET'),false);
});
test('suggestion sends target only an active available identity, not a renderer reference',async t=>{
  const f=setup(t),identity='d'.repeat(32);
  f.session.control.state='running';f.session.control.actions=['send_suggestion'];
  f.session.control.suggestions={active:true,busy:false,rows:[{id:identity,state:'available'}]};
  await assert.rejects(f.client.submit(f.sessionId,'send_suggestion',undefined,undefined,undefined,'John 3:16'));
  await assert.rejects(f.client.submit(f.sessionId,'send_suggestion',undefined,undefined,undefined,'e'.repeat(32)));
  const result=await f.client.submit(f.sessionId,'send_suggestion',undefined,undefined,undefined,identity);
  const request=JSON.parse(fs.readFileSync(path.join(f.inbox,`command-${result.id}.json`)));
  assert.equal(request.suggestion_id,identity);assert.equal('reference' in request,false);
  f.session.control.suggestions.rows[0].state='sending';
  await assert.rejects(f.client.submit(f.sessionId,'send_suggestion',undefined,undefined,undefined,identity));
  f.session.control.state='stopped';
  await assert.rejects(f.client.submit(f.sessionId,'send_suggestion',undefined,undefined,undefined,identity));
});
test('outline edits are typed, bounded and bound to the current revision and state',async t=>{
  const f=setup(t),revision='d'.repeat(32);
  f.session.control.actions=['edit_outline'];f.session.control.outline={revision,text:''};
  const send=value=>f.client.submit(f.sessionId,'edit_outline',undefined,undefined,undefined,undefined,value);
  await assert.rejects(send({revision:'e'.repeat(32),text:'Stale notes'}));
  await assert.rejects(send({revision,text:'x'.repeat(4001)}));
  await assert.rejects(send({revision,text:'\0'}));
  const result=await send({revision,text:'കുറിപ്പുകൾ <script>plain text</script>'});
  const request=JSON.parse(fs.readFileSync(path.join(f.inbox,`command-${result.id}.json`)));
  assert.equal(request.outline_revision,revision);assert.equal(request.outline_text,'കുറിപ്പുകൾ <script>plain text</script>');
  f.session.control.state='starting';await assert.rejects(send({revision,text:'Unavailable'}));
});

test('session commands carry only bounded opaque identities and reject arbitrary paths, fields and stale permissions',async t=>{
  const f=setup(t);f.session.control.actions=['list_sessions','preview_session','resume_saved','set_worship','save_session','emergency_save'];
  const submit=(action,value)=>f.client.submit(f.sessionId,action,undefined,undefined,undefined,undefined,undefined,value);
  await assert.rejects(submit('preview_session',{record_id:'../../settings',page:0}));
  await assert.rejects(submit('list_sessions',{page:0,path:'/private'}));
  await assert.rejects(submit('list_sessions',{page:-1}));
  await assert.rejects(submit('set_worship',{enabled:'true'}));
  const result=await submit('resume_saved',{record_id:'e'.repeat(32),record_revision:'f'.repeat(32)});
  const request=JSON.parse(fs.readFileSync(path.join(f.inbox,`command-${result.id}.json`)));
  assert.equal(request.record_id,'e'.repeat(32));assert.equal(request.record_revision,'f'.repeat(32));
  assert.equal(f.reader.commandTransition,undefined,'Resume never starts recognition');
  f.session.control.actions=[];await assert.rejects(submit('emergency_save',{}));
});
test('operator decoder bounds archived content and removes private fields',t=>{
  const f=setup(t),fixture={...f.session,schema:1,revision:1,origin:'engine',started_at:new Date(f.now).toISOString(),config:{streams:{primary:{enabled:true},secondary:{enabled:false}}},transcripts:[],delivery_events:[]};
  fixture.control.operator={worship:true,emergency:true,status:'failed',message:'Save failed',key:'PRIVATE',library:{rows:[],selected:{id:'e'.repeat(32),revision:'f'.repeat(32),kind:'session',primary:'x'.repeat(6000),secondary:'മലയാളം',outline:'Notes',sources:{primary:'speech'},languages:{primary:'en'},settings:{key:'PRIVATE'}}}};
  const op=decodeSnapshot(fixture).control.operator;
  assert.equal(op.library.selected.primary.length,4000);assert.equal(op.library.selected.secondary,'മലയാളം');assert.equal(op.worship,true);
  assert.equal(JSON.stringify(op).includes('PRIVATE'),false);
});

test('connection commands bind saved revision, exact role/review and credential scope without accepting paths or URLs',async t=>{
 const f=setup(t),revision='d'.repeat(32);f.session.control.actions=['connection_action'];f.session.control.settings={revision};
 const send=v=>f.client.submit(f.sessionId,'connection_action',undefined,undefined,undefined,undefined,undefined,v);
 for(const v of [{operation:'local_test',settings_revision:revision,role:'verse',endpoint:'http://other'}, {operation:'import',settings_revision:revision,attachment_id:'../../key.json',include_credentials:true},{operation:'atem_on',settings_revision:revision,review_id:'e'.repeat(32),isolated:false},{operation:'local_warm',settings_revision:revision,role:'other'}])await assert.rejects(send(v));
 const payload={operation:'local_warm',settings_revision:revision,role:'summary'};const result=await send(payload);const r=JSON.parse(fs.readFileSync(path.join(f.inbox,`command-${result.id}.json`)));assert.deepEqual(Object.fromEntries(Object.keys(payload).map(k=>[k,r[k]])),payload);
 f.snapshot.connection='stale';await assert.rejects(send(payload));
});
