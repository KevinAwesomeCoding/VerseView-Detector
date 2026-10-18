'use strict';
const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), os = require('node:os');
const { BackendManager } = require('../backend-manager.cjs');
const { inventory, verify, relocateLinks } = require('../scripts/backend-integrity.cjs');
function setup(t) {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'vv-backend-manager-'));
  t.after(() => fs.rmSync(base, { recursive: true, force: true }));
  const sourceProfile = path.join(base, 'source'), profile = path.join(base, 'QA', 'Backend'), root = path.join(base, 'backend');
  fs.mkdirSync(sourceProfile); fs.mkdirSync(root);
  fs.writeFileSync(path.join(sourceProfile, 'settings.json'), JSON.stringify({ private_key: 'private', future: { keep: true } }));
  return { base, sourceProfile, profile, root, manager: new BackendManager({ root, sourceProfile, profile }) };
}
test('profile migration copies once, retains secrets/unknowns privately, and never rewrites source', async t => {
  const f = setup(t), source = path.join(f.sourceProfile, 'settings.json'), original = fs.readFileSync(source);
  await f.manager.prepareProfile();
  assert.deepEqual(fs.readFileSync(source), original);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.profile, 'settings.json'))), JSON.parse(original));
  fs.writeFileSync(path.join(f.profile, 'settings.json'), '{"local":"changed"}');
  await f.manager.prepareProfile();
  assert.equal(JSON.parse(fs.readFileSync(path.join(f.profile, 'settings.json'))).local, 'changed');
  assert.equal(JSON.stringify(f.manager.state).includes('private'), false);
});
test('managed GCP credentials are copied into the new profile without changing their source', async t => {
  const f = setup(t), directory = path.join(f.sourceProfile, 'credentials'); fs.mkdirSync(directory);
  const credential = path.join(directory, 'gcp_service_account.json'); fs.writeFileSync(credential, '{"key":"private"}');
  fs.writeFileSync(path.join(f.sourceProfile, 'settings.json'), JSON.stringify({ gcp_credentials_path: credential }));
  await f.manager.prepareProfile();
  const saved = JSON.parse(fs.readFileSync(path.join(f.profile, 'settings.json')));
  assert.equal(saved.gcp_credentials_path, path.join(f.profile, 'credentials', 'gcp_service_account.json'));
  assert.equal(fs.readFileSync(credential, 'utf8'), '{"key":"private"}');
});
test('malformed source settings do not create a replacement profile or launch a process', async t => {
  const f = setup(t); fs.writeFileSync(path.join(f.sourceProfile, 'settings.json'), '{broken');
  await assert.rejects(f.manager.prepareProfile());
  assert.equal(fs.existsSync(path.join(f.profile, 'settings.json')), false);
});
test('missing backend reports unavailable/failure with no automatic restart', async t => {
  const f = setup(t); let calls = 0; f.manager.spawnProcess = () => { calls++; throw new Error('must not spawn'); };
  assert.equal(f.manager.state.status, 'unavailable');
  assert.equal((await f.manager.launch()).status, 'failed'); assert.equal(calls, 0);
});
test('runtime inventory rejects altered files and mismatched platforms', t => {
  const f = setup(t); fs.writeFileSync(path.join(f.root, 'VerseViewBackend'), 'test executable');
  fs.writeFileSync(path.join(f.root, 'backend-manifest.json'), JSON.stringify({ platform: process.platform, arch: process.arch, files: inventory(f.root) }));
  verify(f.root, process.platform, process.arch);
  assert.throws(() => verify(f.root, 'other', process.arch));
  fs.writeFileSync(path.join(f.root, 'VerseViewBackend'), 'changed');
  assert.throws(() => verify(f.root, process.platform, process.arch));
});

test('relocated Python links stay inside the packaged backend after the source disappears', { skip: process.platform === 'win32' }, t => {
  const f = setup(t), destination = path.join(f.base, 'copy'); fs.mkdirSync(destination);
  fs.mkdirSync(path.join(f.root, 'lib')); fs.mkdirSync(path.join(destination, 'lib'));
  fs.writeFileSync(path.join(f.root, 'lib', 'Python'), 'runtime');
  fs.writeFileSync(path.join(destination, 'lib', 'Python'), 'runtime');
  fs.symlinkSync('lib/Python', path.join(f.root, 'Python'));
  fs.symlinkSync(path.join(f.root, 'lib', 'Python'), path.join(destination, 'Python'));
  relocateLinks(f.root, destination, { files: inventory(f.root) });
  fs.rmSync(f.root, { recursive: true });
  assert.equal(fs.readFileSync(path.join(destination, 'Python'), 'utf8'), 'runtime');
  assert.equal(path.isAbsolute(fs.readlinkSync(path.join(destination, 'Python'))), false);
});
