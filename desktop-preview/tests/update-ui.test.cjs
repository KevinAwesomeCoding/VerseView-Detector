'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

test('title bar offers a verified update and reports download or retry states', async () => {
  const handlers = new Map();
  const element = () => ({ dataset: {}, hidden: false, disabled: false, textContent: '', title: '', value: '',
    classList: { toggle() {} }, addEventListener(name, fn) { handlers.set(this.id + ':' + name, fn); } });
  const ids = ['verseview-prototype', 'preview-surface', 'preview-layout', 'preview-mode', 'preview-reset',
    'preview-update-tools', 'preview-update', 'preview-update-status', 'preview-update-prompt',
    'preview-update-prompt-message', 'preview-update-prompt-later', 'preview-update-prompt-apply'];
  const nodes = Object.fromEntries(ids.map(id => [id, Object.assign(element(), { id })]));
  nodes['verseview-prototype'].dispatchEvent = () => {};
  let updateChanged, applied = 0, checked = 0;
  const bridge = { onUpdateChanged(fn) { updateChanged = fn; }, updateState: async () => ({ phase: 'current' }),
    applyUpdate: async () => { applied++; }, checkUpdate: async () => { checked++; },
    onBackendChanged() {}, backendState: async () => ({ status: 'unavailable' }),
    onObserverChanged() {}, observer: async () => ({ connection: 'waiting', sources: [], session: null }),
    onAppearanceChanged() {}, environment: async () => ({ platform: 'darwin', appearance: { mode: 'solid' } }) };
  const window = { verseviewDesktop: bridge };
  const script = fs.readFileSync(path.join(__dirname, '../src/desktop.js'), 'utf8');
  vm.runInNewContext(script, { window, document: { getElementById: id => nodes[id] },
    localStorage: { getItem: () => null, setItem() {} }, Event,
    CustomEvent: class extends Event { constructor(name, value) { super(name); this.detail = value.detail; } } });
  const button = nodes['preview-update'], tools = nodes['preview-update-tools'];
  updateChanged({ phase: 'available', tag: 'desktop-beta-240-1', prerelease: true });
  assert.equal(tools.hidden, false);
  assert.equal(button.textContent, 'Update');
  assert.match(nodes['preview-update-status'].textContent, /Beta desktop-beta-240-1/);
  assert.equal(nodes['preview-update-prompt'].hidden, false);
  assert.match(nodes['preview-update-prompt-message'].textContent, /beta/);
  handlers.get('preview-update-prompt-later:click')();
  assert.equal(nodes['preview-update-prompt'].hidden, true);
  updateChanged({ phase: 'available', tag: 'desktop-beta-240-1', prerelease: true });
  assert.equal(nodes['preview-update-prompt'].hidden, true);
  updateChanged({ phase: 'available', tag: 'desktop-beta-241-1', prerelease: true });
  assert.equal(nodes['preview-update-prompt'].hidden, false);
  await handlers.get('preview-update-prompt-apply:click')();
  assert.equal(applied, 1);
  assert.equal(nodes['preview-update-prompt'].hidden, true);
  updateChanged({ phase: 'downloading', percent: 42 });
  assert.equal(button.disabled, true);
  assert.equal(button.textContent, 'Downloading 42%…');
  updateChanged({ phase: 'error', message: 'Checksum mismatch' });
  assert.equal(button.disabled, false);
  assert.equal(nodes['preview-update-status'].textContent, 'Checksum mismatch');
  await handlers.get('preview-update:click')();
  assert.equal(checked, 1);
});
