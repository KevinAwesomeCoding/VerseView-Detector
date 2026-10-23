'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { candidate, checksum, launchInstaller } = require('../update-service.cjs');

const name = 'VerseView-Detector-Mac-Apple-Silicon.zip';
const digest = 'a'.repeat(64);
const current = '1'.repeat(40);
const newer = '2'.repeat(40);
const release = (overrides = {}) => ({ draft: false, prerelease: true, tag_name: 'desktop-beta-240-1',
  published_at: '2026-10-23T12:00:00Z', body: `Source commit: \`${newer}\`\n\n${digest}  ${name}\n`,
  assets: [{ name, size: 100, browser_download_url: `https://github.com/example/${name}` }], ...overrides });
const context = { platform: 'darwin', arch: 'arm64', builtAt: '2026-10-22T12:00:00Z', sourceRevision: current };

test('selects the newest compatible release with a published checksum and different source', () => {
  const old = release({ tag_name: 'older', published_at: '2026-10-22T13:00:00Z' });
  const chosen = candidate([old, release()], context);
  assert.equal(chosen.tag, 'desktop-beta-240-1');
  assert.equal(chosen.sha256, digest);
  assert.equal(chosen.name, name);
  assert.equal(candidate([release({ body: `Source commit: \`${current}\`\n${digest}  ${name}` })], context), null);
  assert.equal(candidate([release({ body: `Source commit: \`${newer}\`` })], context), null);
  assert.equal(candidate([release({ published_at: '2026-10-20T12:00:00Z' })], context), null);
  assert.equal(candidate([release()], { ...context, platform: 'linux' }), null);
  assert.equal(checksum(`${digest}  ${name}`, name), digest);
});

test('selects only the matching Intel Mac or Windows installer asset', () => {
  for (const [platform, arch, assetName] of [
    ['darwin', 'x64', 'VerseView-Detector-Mac-Intel.zip'],
    ['win32', 'x64', 'VerseView-Detector-Windows-Setup.exe']
  ]) {
    const matching = release({ assets: [{ name: assetName, size: 100,
      browser_download_url: `https://github.com/example/${assetName}` }],
      body: `Source commit: \`${newer}\`\n\n${digest}  ${assetName}\n` });
    assert.equal(candidate([matching], { ...context, platform, arch })?.name, assetName);
    assert.equal(candidate([release()], { ...context, platform, arch }), null);
    assert.equal(candidate([matching], { ...context, platform, arch, channel: 'stable' }), null);
  }
});

test('Windows handoff starts the installer in the current executable directory', async () => {
  const calls = [];
  const child = new EventEmitter();
  child.unref = () => calls.push('unref');
  const spawnInstaller = (file, args, options) => {
    calls.push({ file, args, options });
    process.nextTick(() => child.emit('spawn'));
    return child;
  };
  await launchInstaller('C:\\Users\\Test\\AppData\\Local\\Temp\\setup.exe',
    'C:\\Users\\Test\\AppData\\Local\\Programs\\VerseView Detector\\VerseView Detector.exe', spawnInstaller);
  assert.deepEqual(calls[0], {
    file: 'C:\\Users\\Test\\AppData\\Local\\Temp\\setup.exe',
    args: ['/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
      '/DIR=C:\\Users\\Test\\AppData\\Local\\Programs\\VerseView Detector'],
    options: { detached: true, stdio: 'ignore', windowsHide: false }
  });
  assert.equal(calls[1], 'unref');
});
