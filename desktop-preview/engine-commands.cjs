'use strict';
const fs = require('node:fs');
const path = require('node:path');
const settingsPolicy = require('./src/settings-policy.js');
const { randomUUID } = require('node:crypto');

// Only the main process writes commands. No renderer paths, URLs, or arbitrary IPC.
class EngineCommands {
  constructor(reader, { clock = Date.now } = {}) { this.reader = reader; this.clock = clock; }
  async submit(sessionId, action, candidateId, settingsChange, recoveryRevision) {
    if (!['start', 'stop', 'approve', 'reject', 'save_settings', 'panic', 'restore_session', 'discard_session'].includes(action) || !/^[a-f0-9]{32}$/.test(sessionId || '')) {
      throw new Error('Invalid detector command');
    }
    if (['approve', 'reject'].includes(action) && (typeof candidateId !== 'string' || !candidateId || candidateId.length > 128)) {
      throw new Error('Invalid candidate');
    }
    let changes;
    const recoveryAction = ['restore_session', 'discard_session'].includes(action);
    if (recoveryAction && !/^[a-f0-9]{32}$/.test(recoveryRevision || '')) throw new Error('Invalid recovery revision');
    if (action === 'save_settings') {
      if (!/^[a-f0-9]{32}$/.test(settingsChange?.revision || '')) throw new Error('Invalid settings revision');
      changes = settingsPolicy.validatePatch(settingsChange.changes);
    }
    const snapshot = await this.reader.poll();
    const session = snapshot.session;
    const control = session?.control;
    if (snapshot.connection !== 'connected' || session?.session_id !== sessionId || !control
      || this.clock() - Date.parse(session.updated_at) > 6000 || control.state === 'closed') {
      throw new Error('Detector session unavailable; refresh before acting');
    }
    if (['start', 'stop', 'save_settings', 'panic', 'restore_session', 'discard_session'].includes(action) ? !control.actions.includes(action)
      : control.state !== 'running' || !control.pending.some(item => item.candidate_id === candidateId)) {
      throw new Error('Action is no longer available');
    }
    if (action === 'save_settings' && (control.state !== 'stopped' || control.settings?.revision !== settingsChange.revision)) {
      throw new Error('Settings changed or engine is running; reload before saving');
    }
    if (recoveryAction && (control.state !== 'stopped' || control.recovery?.revision !== recoveryRevision)) {
      throw new Error('Recovery changed or engine is running; refresh before acting');
    }
    const directory = path.join(this.reader.directory, `control-${session.pid}-${control.id}`);
    const stat = await fs.promises.lstat(directory);
    if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error('Invalid detector inbox');
    const id = randomUUID().replaceAll('-', '');
    const request = { id, control_id: control.id, session_id: sessionId, action, created_at: this.clock() / 1000,
      ...(['approve', 'reject'].includes(action) ? { candidate_id: candidateId } : {}),
      ...(action === 'save_settings' ? { settings_revision: settingsChange.revision, changes } : {}),
      ...(recoveryAction ? { recovery_revision: recoveryRevision } : {}) };
    const temporary = path.join(directory, `.command-${id}.tmp`);
    try {
      await fs.promises.writeFile(temporary, JSON.stringify(request), { encoding: 'utf8', mode: 0o600, flag: 'wx' });
      await fs.promises.rename(temporary, path.join(directory, `command-${id}.json`));
    } finally { await fs.promises.unlink(temporary).catch(error => { if (error.code !== 'ENOENT') throw error; }); }
    if (action === 'start') this.reader.commandTransition = { id, pid: session.pid, controlId: control.id,
      sessionId, deadline: this.clock() + 12000 };
    // This acknowledges only the local write. Result and engine status arrive through the feed.
    return { id, action, outcome: 'submitted' };
  }
}
module.exports = { EngineCommands };
