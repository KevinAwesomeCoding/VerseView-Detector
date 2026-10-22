'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const policy = require('../src/settings-policy.js');
const { EngineCommands } = require('../engine-commands.cjs');
const values = { language: 'English', stt_engine: 'deepgram', dual_stt_enabled: false,
  secondary_language: null, secondary_stt_engine: 'deepgram', mic_index: 0,
  bible_translation: 'KJV', remote_url: 'http://127.0.0.1:50010/control.html' };
test('settings boundary allows only typed non-secret fields', () => {
  assert.deepEqual(policy.validatePatch({ mic_index: 2, dual_stt_enabled: true }), { mic_index: 2, dual_stt_enabled: true });
  assert.deepEqual(policy.validatePatch({confidence:.9,manual_confirm:false,verify:true,verse_interrupt:true,spoken_numeral_mode:true,smart_amen:false}),
    {confidence:.9,manual_confirm:false,verify:true,verse_interrupt:true,spoken_numeral_mode:true,smart_amen:false});
  for (const patch of [{ api_key: 'private' }, { manual_confirm: 'false' }, { confidence: NaN }, { confidence: .49 }, { confidence: true }, { confidence: 1.01 }, { mic_index: true }, { mic_index: -1 },
    { changes: {} }, { language: [] }, { stt_engine: 'unknown' }, { bible_translation: 'bad' }]) {
    assert.throws(() => policy.validatePatch(patch));
  }
});
test('settings URLs exclude secrets, file schemes and malformed ports', () => {
  for (const url of ['file:///tmp/a', 'http://user:password@host/', 'http://host/?token=private',
    'http://host/#private', 'http://host:0/', 'http://host:99999/', 'http://bad host/']) {
    assert.throws(() => policy.validatePatch({ remote_url: url }), url);
  }
  for (const url of ['https://computer.local/control.html', 'http://[::1]:50010/control.html']) {
    assert.equal(policy.validatePatch({ remote_url: url }).remote_url, url);
  }
});
test('settings decoder drops arbitrary fields and invalid URLs', () => {
  const decoded = policy.decode({ revision: 'a'.repeat(32), values: { ...values, api_key: 'private', remote_url: 'http://u:private@host' },
    devices: [{ id: 0, label: 'Test microphone', api_key: 'private' }] });
  assert.equal(decoded.values.remote_url, '');
  assert.equal(JSON.stringify(decoded).includes('private'), false);
  assert.equal(policy.decode({ revision: '../../settings', values, devices: [] }), null);
});
test('supported provider options depend on language', () => {
  assert.equal(policy.providersFor('ml').includes('deepgram'), false);
  assert.equal(policy.providersFor('ml').includes('gcp'), true);
  assert.equal(policy.providersFor('hi').includes('assemblyai_pro'), false);
  assert.equal(policy.providersFor('multi').includes('assemblyai_multilingual'), true);
});
function setup(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'vv-settings-boundary-'));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const session = { pid: 100, session_id: 'a'.repeat(32), updated_at: new Date().toISOString(),
    control: { id: 'b'.repeat(32), state: 'stopped', actions: ['start', 'save_settings'],
      settings: { revision: 'c'.repeat(32), values, devices: [] } } };
  const snapshot = { session, connection: 'connected' };
  const inbox = path.join(directory, `control-100-${session.control.id}`); fs.mkdirSync(inbox);
  return { session, snapshot, inbox, client: new EngineCommands({ directory, poll: async () => snapshot }) };
}
test('settings requests carry exact host/session/revision and bounded changes', async t => {
  const f = setup(t);
  const result = await f.client.submit(f.session.session_id, 'save_settings', undefined,
    { revision: f.session.control.settings.revision, changes: { mic_index: 2 } });
  const request = JSON.parse(fs.readFileSync(path.join(f.inbox, `command-${result.id}.json`)));
  assert.equal(result.outcome, 'submitted');
  assert.equal(request.settings_revision, f.session.control.settings.revision);
  assert.deepEqual(request.changes, { mic_index: 2 });
});
test('running, stale, read-only and changed settings reject submission without writes', async t => {
  const f = setup(t), update = { revision: f.session.control.settings.revision, changes: { mic_index: 2 } };
  f.session.control.state = 'running';
  await assert.rejects(f.client.submit(f.session.session_id, 'save_settings', undefined, update));
  f.session.control.state = 'stopped'; f.snapshot.connection = 'stale';
  await assert.rejects(f.client.submit(f.session.session_id, 'save_settings', undefined, update));
  f.snapshot.connection = 'connected'; f.session.control.actions = ['start'];
  await assert.rejects(f.client.submit(f.session.session_id, 'save_settings', undefined, update));
  f.session.control.actions = ['save_settings']; update.revision = 'd'.repeat(32);
  await assert.rejects(f.client.submit(f.session.session_id, 'save_settings', undefined, update));
  assert.deepEqual(fs.readdirSync(f.inbox), []);
});

test('watcher settings expose setup while Off and strictly bound developer tuning',()=>{
 assert.deepEqual(policy.validatePatch({watcher_enabled:false,watcher_provider:'local',watcher_window_lines:12}),{watcher_enabled:false,watcher_provider:'local',watcher_window_lines:12});
 for(const value of [{watcher_enabled:'yes'},{watcher_provider:'bad'},{watcher_batch_interval:0},{watcher_cooldown:NaN},{watcher_window_lines:1.5},{watcher_passive_confidence:1.1}])assert.throws(()=>policy.validatePatch(value));
 const decoded=policy.decode({revision:'a'.repeat(32),devices:[],values:{...values,watcher_enabled:false,watcher_provider:'local',watcher_api_key:'PRIVATE'}});
 assert.equal(decoded.values.watcher_provider,'local');assert.equal(decoded.values.watcher_enabled,false);assert.equal(JSON.stringify(decoded).includes('PRIVATE'),false);
});
