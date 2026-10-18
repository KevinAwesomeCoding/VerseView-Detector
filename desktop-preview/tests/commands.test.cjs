'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { EngineCommands } = require('../engine-commands.cjs');
const { EngineFeedReader, decodeSnapshot } = require('../engine-feed.cjs');
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
  fs.writeFileSync(file, JSON.stringify(fixture));
  await reader.poll(); await reader.select(f.sessionId);
  const client = new EngineCommands(reader, { clock: () => f.now });
  const result = await client.submit(f.sessionId, 'start');
  fixture.session_id = 'c'.repeat(32);
  fixture.control.results = [{ id: result.id, action: 'start', outcome: 'requested' }];
  fs.writeFileSync(file, JSON.stringify(fixture));
  assert.equal((await reader.poll()).selected, fixture.session_id);
  assert.equal(reader.snapshot.connection, 'connected');
  fixture.session_id = 'd'.repeat(32); fixture.control.results = [];
  fs.writeFileSync(file, JSON.stringify(fixture));
  assert.equal((await reader.poll()).connection, 'unavailable');
});
test('control decoder exposes only bounded typed fields', t => {
  const f = setup(t);
  const decoded = decodeSnapshot({ ...f.session, schema: 1, revision: 1, origin: 'engine',
    started_at: new Date(f.now).toISOString(), config: { streams: { primary: { enabled: true }, secondary: { enabled: false } } },
    transcripts: [], delivery_events: [], control: { ...f.session.control, secret: 'private', actions: ['start', 'goto'] } });
  assert.deepEqual(decoded.control.actions, ['start']);
  assert.equal(JSON.stringify(decoded).includes('private'), false);
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
