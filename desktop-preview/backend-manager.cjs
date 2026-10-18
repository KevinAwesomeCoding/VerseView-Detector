'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');
const readline = require('node:readline');

class BackendManager {
  constructor({ root, profile, sourceProfile, verification = false, onChange = () => {}, spawnProcess = spawn }) {
    Object.assign(this, { root, profile, sourceProfile, verification, onChange, spawnProcess });
    this.state = { status: fs.existsSync(path.join(root, 'backend-manifest.json')) ? 'available' : 'unavailable',
      message: 'Launch the bundled backend; recognition stays stopped.', pid: null, owned: false };
  }
  update(patch) { this.state = { ...this.state, ...patch }; this.onChange(this.state); return this.state; }
  async prepareProfile() {
    await fs.promises.mkdir(this.profile, { recursive: true, mode: 0o700 });
    const target = path.join(this.profile, 'settings.json');
    try { await fs.promises.access(target); return; } catch (error) { if (error.code !== 'ENOENT') throw error; }
    let data = '{}';
    try { data = await fs.promises.readFile(path.join(this.sourceProfile, 'settings.json'), 'utf8'); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
    const value = JSON.parse(data);
    if (!value || Array.isArray(value) || typeof value !== 'object') throw new Error('Invalid existing settings');
    const sourceCredentials = path.join(this.sourceProfile, 'credentials');
    const credentials = path.join(this.profile, 'credentials');
    try {
      const entries = await fs.promises.readdir(sourceCredentials, { withFileTypes: true });
      await fs.promises.mkdir(credentials, { recursive: true, mode: 0o700 });
      for (const entry of entries.filter(item => item.isFile() && item.name.endsWith('.json'))) {
        const data = await fs.promises.readFile(path.join(sourceCredentials, entry.name));
        await fs.promises.writeFile(path.join(credentials, entry.name), data, { flag: 'wx', mode: 0o600 }).catch(error => { if (error.code !== 'EEXIST') throw error; });
      }
      if (value.gcp_credentials_path && path.dirname(path.resolve(value.gcp_credentials_path)) === path.resolve(sourceCredentials)) {
        value.gcp_credentials_path = path.join(credentials, path.basename(value.gcp_credentials_path));
      }
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
    // Copy once into a private preview profile; never rewrite the source profile.
    await fs.promises.writeFile(target, JSON.stringify(value, null, 2), { mode: 0o600, flag: 'wx' });
  }
  async launch() {
    if (this.child) return this.state;
    if (this.launching) return this.launching;
    this.launching = this.start();
    try { return await this.launching; } finally { this.launching = null; }
  }
  async start() {
    this.update({ status: 'starting', message: 'Starting the backend host; recognition remains stopped.' });
    try {
      const manifest = JSON.parse(await fs.promises.readFile(path.join(this.root, 'backend-manifest.json'), 'utf8'));
      if (manifest.platform !== process.platform || manifest.arch !== process.arch) throw new Error('Wrong native backend');
      const name = process.platform === 'win32' ? 'VerseViewBackend.exe' : 'VerseViewBackend';
      const executable = path.join(this.root, name);
      const digest = crypto.createHash('sha256').update(await fs.promises.readFile(executable)).digest('hex');
      if (manifest.files[name]?.sha256 !== digest) throw new Error('Backend executable mismatch');
      await this.prepareProfile();
      const env = { ...process.env, VERSEVIEW_PROFILE_DIRECTORY: this.profile };
      for (const key of ['PYTHONHOME', 'PYTHONPATH', 'VV_RUN_BOT']) delete env[key];
      if (this.verification) env.VV_PREVIEW_TEST_PROFILE = '1';
      const args = ['--profile', this.profile, ...(this.verification ? ['--verify-isolated'] : [])];
      const child = this.spawnProcess(executable, args, { cwd: this.profile, env, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
      this.child = child;
      // Raw provider/log output stays outside the renderer; never forward stderr.
      child.stderr.on('data', () => {});
      child.stdin.on('error', () => {});
      const lines = readline.createInterface({ input: child.stdout });
      await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error('Backend ready timeout')), 20000);
        child.once('error', error => { clearTimeout(timeout); reject(error); });
        child.once('exit', (code, signal) => {
          clearTimeout(timeout);
          this.child = null;
          const expected = this.state.status === 'closing';
          this.update({ status: expected && code === 0 ? 'available' : 'failed', owned: false, pid: null,
            message: expected && code === 0 ? 'Backend closed. Recognition is stopped.' : 'Backend exited. Inspect its private log; no automatic restart.' });
          reject(new Error(`Backend exited ${code ?? signal}`));
        });
        lines.on('line', line => {
          try {
            const message = JSON.parse(line);
            if (message.ready === true && message.pid === child.pid && message.frozen === true && message.guiImported === false
                && message.verification === this.verification && this.state.status !== 'closing') {
              clearTimeout(timeout);
              this.update({ status: 'ready', message: this.verification ? 'Isolated verification backend · no microphone or live services' : 'Backend ready. Press Start engine when ready for recognition.',
                pid: child.pid, owned: true, frozen: true, guiImported: false, verification: this.verification });
              resolve();
            }
          } catch { /* Only the allowlisted ready protocol is interpreted. */ }
        });
      });
      return this.state;
    } catch {
      if (this.child) await this.close();
      return this.update({ status: 'failed', message: 'Backend could not start. Check its private log and native package.', owned: !!this.child, pid: this.child?.pid || null });
    }
  }
  async close() {
    const child = this.child;
    if (!child) return this.state;
    if (this.closing) return this.closing;
    this.update({ status: 'closing', message: 'Stopping recognition and closing the owned backend.' });
    this.closing = new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.update({ status: 'stop_timeout', message: 'Backend is still stopping. The app stays open for cleanup.' });
        reject(new Error('Backend still stopping'));
      }, 30000);
      child.once('exit', () => { clearTimeout(timeout); resolve(this.state); });
      if (!child.stdin.destroyed) child.stdin.end(JSON.stringify({ action: 'shutdown' }) + '\n');
    });
    try { return await this.closing; } finally { this.closing = null; }
  }
}
module.exports = { BackendManager };
