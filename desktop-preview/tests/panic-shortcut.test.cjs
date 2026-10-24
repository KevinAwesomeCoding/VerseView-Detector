'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { PanicShortcut } = require('../panic-shortcut.cjs');

const id = 'a'.repeat(32);
function feed(shortcut = 'Shift+Escape', state = 'running', connection = 'connected', sessionId = id) {
  return { connection, session: { session_id: sessionId, control: {
    state, actions: state === 'running' ? ['panic'] : [], settings: { values: { desktop_panic_shortcut: shortcut } }
  } } };
}
function harness(register = true) {
  const bindings = new Map(), calls = [], statuses = [];
  const globalShortcut = {
    register: (accelerator, callback) => {
      calls.push(['register', accelerator]);
      if (!register) return false;
      bindings.set(accelerator, callback);
      return true;
    },
    unregister: accelerator => { calls.push(['unregister', accelerator]); bindings.delete(accelerator); }
  };
  const commands = { submit: async (sessionId, action) => { calls.push(['submit', sessionId, action]); } };
  let now = 1000;
  const shortcut = new PanicShortcut({ globalShortcut, commands, onChange: value => statuses.push(value), clock: () => now });
  return { shortcut, bindings, calls, statuses, advance: ms => { now += ms; } };
}

test('registers saved shortcut, sends panic across apps, and releases it on Stop', async () => {
  const h = harness();
  h.shortcut.sync(feed());
  assert.equal(h.shortcut.snapshot().state, 'ready');
  assert.equal(h.bindings.has('Shift+Escape'), true);
  h.bindings.get('Shift+Escape')();
  assert.deepEqual(h.calls.at(-1), ['submit', id, 'panic']);
  h.bindings.get('Shift+Escape')();
  assert.equal(h.calls.filter(call => call[0] === 'submit').length, 1);
  h.advance(500);
  h.bindings.get('Shift+Escape')();
  assert.equal(h.calls.filter(call => call[0] === 'submit').length, 2);
  h.shortcut.sync(feed('Shift+Escape', 'stopped'));
  assert.equal(h.bindings.size, 0);
  assert.equal(h.shortcut.snapshot().state, 'inactive');
});

test('changes binding and follows the current detector session', () => {
  const h = harness();
  h.shortcut.sync(feed());
  h.shortcut.sync(feed('F8'));
  assert.equal(h.bindings.has('F8'), true);
  h.shortcut.sync(feed('Control+Meta+Shift+P', 'running', 'connected', 'b'.repeat(32)));
  assert.equal(h.bindings.has('Shift+Escape'), false);
  assert.equal(h.bindings.has('F8'), false);
  assert.equal(h.bindings.has('Control+Meta+Shift+P'), true);
  h.bindings.get('Control+Meta+Shift+P')();
  assert.deepEqual(h.calls.at(-1), ['submit', 'b'.repeat(32), 'panic']);
  h.shortcut.sync(feed('Control+Meta+Shift+P', 'running', 'stale'));
  assert.equal(h.bindings.size, 0);
});

test('reports OS registration conflicts and command failures', async () => {
  const unavailable = harness(false);
  unavailable.shortcut.sync(feed());
  assert.equal(unavailable.shortcut.snapshot().state, 'unavailable');
  assert.match(unavailable.shortcut.snapshot().message, /different shortcut/);
  const h = harness();
  h.shortcut.commands.submit = async () => { throw new Error('backend unavailable'); };
  h.shortcut.sync(feed());
  h.bindings.get('Shift+Escape')();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.shortcut.snapshot().state, 'error');
  assert.match(h.shortcut.snapshot().message, /backend unavailable/);
  h.shortcut.stop();
  assert.equal(h.bindings.size, 0);
});
