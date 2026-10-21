'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { applyThemeIcon, iconPath, loadICNS } = require('../theme-icons.cjs');
const fs = require('node:fs');

test('untrusted icon names and extensions cannot select arbitrary files', () => {
  for (const value of ['../app_icon', 'Sage', '', null]) assert.throws(() => iconPath(value));
  assert.throws(() => iconPath('sage', '../png'));
});

test('Windows routes a theme-specific ICO to the window with a PNG fallback', () => {
  const requests = [], applied = [], image = { isEmpty: () => false };
  const window = { isDestroyed: () => false, setIcon: value => applied.push(value) };
  let status = applyThemeIcon({ app: {}, window, theme: 'ember', platform: 'win32',
    nativeImage: { createFromPath: file => { requests.push(file); return image; } } });
  assert.match(requests[0], /verseview-ember\.ico$/);
  assert.equal(applied[0], image);
  assert.equal(status.format, 'ico');
  status = applyThemeIcon({ app: {}, window, theme: 'glass', platform: 'win32',
    nativeImage: { createFromPath: file => ({ isEmpty: () => file.endsWith('.ico') }) } });
  assert.equal(status.format, 'png');
  assert.throws(() => applyThemeIcon({ app: {}, window, theme: 'sage', platform: 'win32',
    nativeImage: { createFromPath: () => ({ isEmpty: () => true }) } }));
});

test('every native ICNS contains a decodable 1024px PNG representation', () => {
  for (const theme of ['sage', 'midnight', 'galaxy', 'aurora', 'ember', 'glass']) {
    const image = loadICNS(iconPath(theme, 'icns'), { createFromBuffer: bytes => {
      assert.equal(bytes.toString('ascii', 1, 4), 'PNG');
      return { isEmpty: () => false, getSize: () => ({ width: bytes.readUInt32BE(16) }) };
    } });
    assert.equal(image.getSize().width, 1024);
    assert.ok(fs.statSync(iconPath(theme, 'ico')).size > 0);
  }
});


test('original icon assets retain the old app icon bytes', () => {
  const path = require('node:path');
  for (const extension of ['png', 'icns', 'ico']) {
    assert.deepEqual(fs.readFileSync(iconPath('original', extension)),
      fs.readFileSync(path.join(__dirname, '../..', `app_icon.${extension}`)));
  }
});

test('native startup defaults to the original icon and safely persists explicit theme choices', () => {
  const { loadAppearance, saveAppearance } = require('../appearance-preferences.cjs');
  const path = require('node:path'), os = require('node:os');
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'vv-appearance-'));
  const file = path.join(directory, 'appearance.json');
  try {
    assert.deepEqual(loadAppearance(file), { theme: 'glass', themedIcon: false });
    saveAppearance(file, { theme: 'ember', themedIcon: true });
    assert.deepEqual(loadAppearance(file), { theme: 'ember', themedIcon: true });
    assert.throws(() => saveAppearance(file, { theme: '../x', themedIcon: true }));
    assert.throws(() => saveAppearance(file, { theme: 'glass', themedIcon: 'yes' }));
    fs.writeFileSync(file, '{bad json');
    assert.deepEqual(loadAppearance(file), { theme: 'glass', themedIcon: false });
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});
