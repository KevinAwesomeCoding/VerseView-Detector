'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const script = fs.readFileSync(path.join(__dirname, '../src/desktop.js'), 'utf8');

function launch(storage) {
  const handlers = new Map();
  const element = () => ({ dataset: {}, hidden: false, disabled: false, textContent: '', title: '', value: '', open: false,
    classList: { toggle() {} }, addEventListener(name, fn) { handlers.set(this.id + ':' + name, fn); },
    showModal() { this.open = true; }, close() { this.open = false; } });
  const ids = ['verseview-prototype', 'preview-surface', 'preview-layout', 'preview-mode', 'preview-reset',
    'preview-update-tools', 'preview-update', 'preview-update-status', 'preview-update-prompt',
    'preview-update-prompt-message', 'preview-update-prompt-notes', 'preview-update-prompt-later',
    'preview-update-prompt-apply'];
  const nodes = Object.fromEntries(ids.map(id => [id, Object.assign(element(), { id })]));
  nodes['verseview-prototype'].dispatchEvent = () => {};
  let updateChanged, applied = 0, checked = 0;
  const bridge = { onUpdateChanged(fn) { updateChanged = fn; }, updateState: async () => ({ phase: 'current' }),
    applyUpdate: async () => { applied++; }, checkUpdate: async () => { checked++; },
    onBackendChanged() {}, backendState: async () => ({ status: 'unavailable' }),
    onObserverChanged() {}, observer: async () => ({ connection: 'waiting', sources: [], session: null }),
    onAppearanceChanged() {}, environment: async () => ({ platform: 'darwin', appearance: { mode: 'solid' } }) };
  vm.runInNewContext(script, { window: { verseviewDesktop: bridge }, document: { getElementById: id => nodes[id] },
    localStorage: { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) }, Event,
    CustomEvent: class extends Event { constructor(name, value) { super(name); this.detail = value.detail; } } });
  return { nodes, handlers, update: value => updateChanged(value), counts: () => ({ applied, checked }) };
}

test('a release prompts once across restarts, while Update reopens its notes and a newer release prompts again', async () => {
  const storage = new Map();
  const first = launch(storage);
  const available = { phase: 'available', tag: 'desktop-beta-240-1', prerelease: true, notes: 'Fixed stream status.' };
  first.update(available);
  assert.equal(first.nodes['preview-update-prompt'].open, true);
  assert.match(first.nodes['preview-update-prompt-notes'].textContent, /Fixed stream status/);
  first.handlers.get('preview-update-prompt-later:click')();
  assert.equal(first.nodes['preview-update-prompt'].open, false);
  first.update(available);
  assert.equal(first.nodes['preview-update-prompt'].open, false);
  assert.equal(first.nodes['preview-update-tools'].hidden, false);

  const reopened = launch(storage);
  reopened.update(available);
  assert.equal(reopened.nodes['preview-update-prompt'].open, false);
  reopened.handlers.get('preview-update:click')();
  assert.equal(reopened.nodes['preview-update-prompt'].open, true);
  reopened.handlers.get('preview-update-prompt-later:click')();
  reopened.update({ ...available, tag: 'desktop-beta-242-1', notes: 'Added new controls.' });
  assert.equal(reopened.nodes['preview-update-prompt'].open, true);
  assert.match(reopened.nodes['preview-update-prompt-notes'].textContent, /Added new controls/);
  await reopened.handlers.get('preview-update-prompt-apply:click')();
  assert.equal(reopened.counts().applied, 1);
  assert.equal(reopened.nodes['preview-update-prompt'].open, false);
  reopened.update({ phase: 'downloading', percent: 42 });
  assert.equal(reopened.nodes['preview-update'].textContent, 'Downloading 42%…');
  reopened.update({ phase: 'error', message: 'Checksum mismatch' });
  assert.equal(reopened.nodes['preview-update-status'].textContent, 'Checksum mismatch');
  reopened.handlers.get('preview-update:click')();
  assert.equal(reopened.counts().checked, 1);
});
