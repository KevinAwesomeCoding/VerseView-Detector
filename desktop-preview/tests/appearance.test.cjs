'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { THEMES, DARK_THEMES, validTheme, backdropPolicy, backgroundColor } = require('../appearance.cjs');
const defaults = { platform: 'darwin', release: '25.0.0', theme: 'glass', reducedTransparency: false, highContrast: false };
const policy = overrides => backdropPolicy({ ...defaults, ...overrides });

test('macOS Glass uses native vibrancy', () => assert.equal(policy({}).material, 'under-window'));
test('Windows 11 22H2 uses acrylic', () => {
  assert.equal(policy({ platform: 'win32', release: '10.0.22621' }).material, 'acrylic');
  assert.equal(policy({ platform: 'win32', release: '10.0.26100' }).mode, 'native');
});
test('Windows 10, early Windows 11, and unknown releases have a solid fallback', () => {
  for (const release of ['10.0.19045', '10.0.22000', '', 'unknown']) {
    assert.equal(policy({ platform: 'win32', release }).mode, 'solid', release);
  }
});
test('accessibility preferences override native effects on both platforms', () => {
  for (const platform of ['darwin', 'win32']) {
    for (const preference of ['reducedTransparency', 'highContrast']) {
      assert.equal(policy({ platform, release: '10.0.26100', [preference]: true }).mode, 'solid');
    }
  }
});
test('other themes never enable native transparency', () => {
  for (const theme of THEMES.filter(value => value !== 'glass')) assert.equal(policy({ theme }).mode, 'solid');
});
test('unknown appearance input is rejected instead of passed to a native API', () => {
  for (const value of ['../../settings', {}, null, 'GLASS']) {
    assert.equal(validTheme(value), false);
    assert.throws(() => policy({ theme: value }), /Unknown theme/);
  }
});
test('all fallback colors are opaque, with fixed dark themes independent of system appearance', () => {
  for (const theme of THEMES) {
    assert.match(backgroundColor(theme, false), /^#[0-9a-f]{6}$/);
    assert.match(backgroundColor(theme, true), /^#[0-9a-f]{6}$/);
    if (DARK_THEMES.has(theme)) assert.equal(backgroundColor(theme, false), backgroundColor(theme, true));
  }
});
