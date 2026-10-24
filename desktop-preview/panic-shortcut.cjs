'use strict';

const policy = require('./src/session-policy.js');

// The OS owns this binding, so it also fires when another application has focus.
class PanicShortcut {
  constructor({ globalShortcut, commands, onChange = () => {}, clock = Date.now }) {
    this.globalShortcut = globalShortcut;
    this.commands = commands;
    this.onChange = onChange;
    this.clock = clock;
    this.accelerator = null;
    this.sessionId = null;
    this.lastTrigger = 0;
    this.status = { state: 'inactive', shortcut: null, message: 'Starts when listening begins.' };
  }

  snapshot() { return { ...this.status }; }

  setStatus(state, shortcut, message) {
    const next = { state, shortcut, message };
    if (JSON.stringify(next) !== JSON.stringify(this.status)) {
      this.status = next;
      this.onChange(this.snapshot());
    }
  }

  release() {
    if (this.accelerator) this.globalShortcut.unregister(this.accelerator);
    this.accelerator = null;
    this.sessionId = null;
    this.lastTrigger = 0;
  }

  sync(snapshot) {
    const control = snapshot?.session?.control;
    const value = control?.settings?.values?.desktop_panic_shortcut;
    const active = snapshot?.connection === 'connected' && control?.state === 'running'
      && control.actions?.includes('panic') && policy.shortcut(value);
    if (!active) {
      this.release();
      this.setStatus('inactive', policy.shortcut(value) ? value : null, 'Starts when listening begins.');
      return;
    }
    const accelerator = value;
    this.sessionId = snapshot.session.session_id;
    if (this.accelerator === accelerator) return;
    this.release();
    this.sessionId = snapshot.session.session_id;
    try {
      if (!this.globalShortcut.register(accelerator, () => this.trigger())) {
        this.setStatus('unavailable', value, 'This shortcut is in use by macOS, Windows, or another app. Choose a different shortcut and restart listening.');
        return;
      }
      this.accelerator = accelerator;
      this.setStatus('ready', value, 'Ready across apps while listening.');
    } catch (error) {
      this.setStatus('unavailable', value, `Could not register shortcut: ${error.message}`);
    }
  }

  trigger() {
    if (!this.sessionId) return;
    const now = this.clock();
    if (now - this.lastTrigger < 500) return;
    this.lastTrigger = now;
    const sessionId = this.sessionId, accelerator = this.accelerator;
    this.commands.submit(sessionId, 'panic').then(() => {
      if (this.sessionId === sessionId && this.accelerator === accelerator)
        this.setStatus('ready', this.status.shortcut, 'Ready across apps while listening.');
    }).catch(error => {
      if (this.sessionId === sessionId && this.accelerator === accelerator)
        this.setStatus('error', this.status.shortcut, `Shortcut pressed, but the clear request could not be sent: ${error.message}`);
    });
  }

  stop() {
    this.release();
    this.setStatus('inactive', null, 'Starts when listening begins.');
  }
}

module.exports = { PanicShortcut };
