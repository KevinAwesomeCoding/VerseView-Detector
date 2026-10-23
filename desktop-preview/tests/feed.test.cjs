'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { EngineFeedReader, decodeSnapshot, feedDirectory, FRESH_MS } = require('../engine-feed.cjs');
const now = Date.now();
const fixture = (pid = 100, session = 'a'.repeat(32)) => ({ schema: 1, pid, session_id: session, revision: 1,
  origin: 'engine', started_at: new Date(now).toISOString(), updated_at: new Date(now).toISOString(), engine_state: 'running',
  config: { bible_translation: 'KJV', streams: { primary: { language: 'en', provider: 'deepgram', enabled: true },
    secondary: { language: 'ml', provider: 'sarvam', enabled: true } } }, streams: {}, transcripts: [], delivery_events: [] });

test('feed location uses native Windows and macOS path conventions', () => {
  assert.equal(feedDirectory({ platform: 'win32', appData: 'C:\\Users\\Test\\AppData\\Roaming' }),
    'C:\\Users\\Test\\AppData\\Roaming\\VerseView\\Observer');
  assert.equal(feedDirectory({ platform: 'darwin', appData: '/Users/test/Library/Application Support' }),
    '/Users/test/Library/Application Support/VerseView/Observer');
});
test('connection status crosses the feed boundary without driver secrets or arbitrary retry counts',()=>{
  const value=fixture();
  value.remote_connection={status:'retrying',attempt:2,maximum:999,retry_seconds:999,reason:'remote',timestamp:value.updated_at,url:'SECRET',exception:'PRIVATE'};
  value.connection_events=Array(20).fill(value.remote_connection);
  const decoded=decodeSnapshot(value,now);
  assert.equal(decoded.remote_connection.maximum,5);assert.equal(decoded.remote_connection.retry_seconds,5);
  assert.equal(decoded.connection_events.length,16);
  assert.equal(JSON.stringify(decoded).includes('SECRET'),false);assert.equal(JSON.stringify(decoded).includes('PRIVATE'),false);
  value.remote_connection.attempt=6;assert.equal(decodeSnapshot(value,now).remote_connection,null);
});
test('decoder drops extra fields and preserves stream/language/candidate identity', () => {
  const value = fixture();
  value.api_key = 'secret';
  value.transcripts = [{ id: 't1', text: '<script>speech</script>', stream: 'secondary', language: 'ml', timestamp: value.updated_at, is_final: true }];
  value.delivery_events = [{ candidate_id: 'candidate-1', reference: 'John 3:16', stream: 'secondary',
    timestamp: value.updated_at, language: 'ml', outcome: 'COMMAND_ACCEPTED', transcript_id: 't1',
    trigger_text: 'യോഹന്നാൻ 3:16', api_key: 'secret' }];
  const decoded = decodeSnapshot(value, now);
  assert.equal(decoded.delivery_events[0].candidate_id, 'candidate-1');
  assert.equal(decoded.transcripts[0].stream, 'secondary');
  assert.equal(decoded.transcripts[0].language, 'ml');
  assert.equal(JSON.stringify(decoded).includes('secret'), false);
  assert.equal(decoded.delivery_events[0].outcome, 'COMMAND_ACCEPTED');
  assert.equal(decoded.delivery_events[0].transcript_id, 't1');
  assert.equal(decoded.delivery_events[0].trigger_text, 'യോഹന്നാൻ 3:16');
});
test('unknown attribution remains unknown and malformed/future snapshots are rejected', () => {
  const value = fixture();
  value.transcripts = [{ text: 'unknown', stream: 'other', timestamp: value.updated_at }];
  assert.equal(decodeSnapshot(value, now).transcripts[0].stream, 'unknown');
  assert.throws(() => decodeSnapshot({ ...value, schema: 2 }, now));
  assert.throws(() => decodeSnapshot({ ...value, updated_at: new Date(now + 60000).toISOString() }, now));
});
test('reader handles waiting, malformed files, heartbeat loss, recovery, and session replacement', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'vv-feed-test-'));
  let clock = now;
  const updates = [];
  const reader = new EngineFeedReader({ directory, clock: () => clock, onChange: value => updates.push(value) });
  const target = path.join(directory, 'engine-100.json');
  try {
    assert.equal((await reader.poll()).connection, 'waiting');
    fs.writeFileSync(target, '{broken');
    assert.equal((await reader.poll()).connection, 'invalid');
    fs.writeFileSync(target, JSON.stringify(fixture()));
    assert.equal((await reader.poll()).connection, 'connected');
    const count = updates.length;
    await reader.poll();
    assert.equal(updates.length, count, 'Heartbeat polling must not repaint unchanged content');
    clock += FRESH_MS + 1;
    assert.equal((await reader.poll()).connection, 'stale');
    const replacement = { ...fixture(100, 'b'.repeat(32)), updated_at: new Date(clock).toISOString() };
    fs.writeFileSync(target, JSON.stringify(replacement));
    assert.equal((await reader.poll()).session.session_id, 'b'.repeat(32));
    assert.equal(reader.snapshot.connection, 'connected');
    fs.writeFileSync(target, 'x'.repeat(2 * 1024 * 1024 + 1));
    assert.equal((await reader.poll()).connection, 'invalid');
  } finally { reader.stop(); fs.rmSync(directory, { recursive: true, force: true }); }
});
test('multiple active engines require explicit selection and never silently switch', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'vv-feed-test-'));
  const reader = new EngineFeedReader({ directory, clock: () => now });
  try {
    fs.writeFileSync(path.join(directory, 'engine-100.json'), JSON.stringify(fixture()));
    fs.writeFileSync(path.join(directory, 'engine-200.json'), JSON.stringify(fixture(200, 'b'.repeat(32))));
    assert.equal((await reader.poll()).connection, 'ambiguous');
    assert.equal(reader.snapshot.session, null);
    assert.equal((await reader.select('b'.repeat(32))).session.pid, 200);
    fs.unlinkSync(path.join(directory, 'engine-200.json'));
    assert.equal((await reader.poll()).connection, 'unavailable');
    assert.equal(reader.snapshot.session, null);
    assert.throws(() => reader.select('../../settings.json'), /Unknown observer session/);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});
test('old process files do not prevent a new detector from connecting', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'vv-feed-test-'));
  const reader = new EngineFeedReader({ directory, clock: () => now });
  try {
    for (let pid = 1; pid <= 40; pid++) {
      const file = path.join(directory, `engine-${pid}.json`);
      fs.writeFileSync(file, JSON.stringify({ ...fixture(pid), updated_at: new Date(now - 60000).toISOString() }));
      fs.utimesSync(file, new Date(now - 60000), new Date(now - 60000));
    }
    fs.writeFileSync(path.join(directory, 'engine-100.json'), JSON.stringify(fixture()));
    const snapshot = await reader.poll();
    assert.equal(snapshot.connection, 'connected');
    assert.equal(snapshot.session.pid, 100);
    assert.equal(snapshot.sources.length, 32);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});
test('recovery preview is bounded, attributed and excludes arbitrary saved settings', () => {
  const value = fixture();
  value.control = { id:'c'.repeat(32), state:'stopped', actions:['restore_session', 'discard_session', 'arbitrary'],
    recovery: { status:'available', revision:'d'.repeat(32), verse_count:1, saved_at:new Date(now).toISOString(),
      preview:{primary:'a'.repeat(3000), secondary:'യോഹന്നാൻ', languages:{primary:'en',secondary:'ml'},
        references:['John 3:16'], settings:{api_key:'SECRET'}}, settings:{api_key:'SECRET'} } };
  const decoded = decodeSnapshot(value, now);
  assert.equal(decoded.control.recovery.preview.primary.length,2000);
  assert.equal(decoded.control.recovery.preview.languages.secondary,'ml');
  assert.deepEqual(decoded.control.actions,['restore_session','discard_session']);
  assert.equal(JSON.stringify(decoded).includes('SECRET'),false);
  assert.deepEqual(decoded.transcripts,[]);
  assert.deepEqual(decoded.delivery_events,[]);
});
test('warmup status is typed and drops model, endpoint and raw errors', () => {
  const value = fixture();
  value.host = { managed:true, warmup:{status:'failed',total:99,endpoint:'SECRET',roles:[
    {role:'verse',status:'warmed',elapsed_seconds:2.5,model:'SECRET'},
    {role:'summary',status:'failed',elapsed_seconds:Infinity,error:'SECRET'},
    {role:'SECRET',status:'failed',elapsed_seconds:1}]}};
  const decoded = decodeSnapshot(value, now);
  assert.deepEqual(decoded.host.warmup,{status:'failed',total:4,roles:[
    {role:'verse',status:'warmed',elapsed_seconds:2.5},
    {role:'summary',status:'failed',elapsed_seconds:0}]});
  assert.equal(JSON.stringify(decoded).includes('SECRET'),false);
  value.host.warmup.status='SECRET';
  assert.equal(decodeSnapshot(value,now).host.warmup,null);
});
test('watcher suggestions omit raw model payload and bound identities/text',()=>{
  const value=fixture();
  value.control={id:'b'.repeat(32),state:'running',actions:['send_suggestion'],suggestions:{enabled:true,active:true,
    raw:'SECRET',rows:[{id:'d'.repeat(32),reference:'John 3:19',created_at:new Date(now).toISOString(),
      kind:'passive_suggest',state:'available',stream:'secondary',language:'ml',confidence:.7,
      reasoning:'a'.repeat(1000),window_text:'PRIVATE-WINDOW',raw:{key:'SECRET'}}]}};
  const decoded=decodeSnapshot(value,now);
  assert.equal(decoded.control.suggestions.rows[0].reasoning.length,400);
  assert.equal(decoded.control.suggestions.rows[0].stream,'secondary');
  assert.equal(JSON.stringify(decoded).includes('PRIVATE'),false);assert.equal(JSON.stringify(decoded).includes('SECRET'),false);
});
test('outline snapshots expose bounded plain text without private provider fields',()=>{
  const value=fixture();value.control={id:'b'.repeat(32),state:'running',actions:['edit_outline'],outline:{
    revision:'d'.repeat(32),text:'<script>plain notes</script>',source:'model',status:'updated',
    enabled:true,active:true,provider_ready:true,api_key:'SECRET',prompt:'PRIVATE-PROMPT'}};
  const decoded=decodeSnapshot(value,now);
  assert.equal(decoded.control.outline.text,'<script>plain notes</script>');
  assert.equal(JSON.stringify(decoded).includes('SECRET'),false);assert.equal(JSON.stringify(decoded).includes('PRIVATE'),false);
  value.control.outline.text='x'.repeat(4001);assert.equal(decodeSnapshot(value,now).control.outline,null);
});
