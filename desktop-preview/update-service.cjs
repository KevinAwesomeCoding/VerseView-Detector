'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const https = require('node:https');
const crypto = require('node:crypto');
const { Transform } = require('node:stream');
const { pipeline } = require('node:stream/promises');
const { spawn, execFileSync } = require('node:child_process');

const API = 'https://api.github.com/repos/KevinAwesomeCoding/VerseView-Detector/releases?per_page=30';
const ASSETS = {
  'darwin-arm64': 'VerseView-Detector-Mac-Apple-Silicon.zip',
  'darwin-x64': 'VerseView-Detector-Mac-Intel.zip',
  'win32-x64': 'VerseView-Detector-Windows-Setup.exe'
};
const MAX_DOWNLOAD = 900 * 1024 * 1024;
const allowed = url => url.protocol === 'https:' &&
  ['api.github.com', 'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'].includes(url.hostname);

function request(url, redirects = 0) {
  const target = new URL(url);
  if (!allowed(target) || redirects > 5) return Promise.reject(new Error('Unexpected update download location'));
  return new Promise((resolve, reject) => {
    const req = https.get(target, { headers: { 'User-Agent': 'VerseView-Detector-Updater', Accept: 'application/vnd.github+json' }, timeout: 20000 }, res => {
      if ([301, 302, 303, 307, 308].includes(res.statusCode)) {
        res.resume();
        return resolve(request(new URL(res.headers.location || '', target).href, redirects + 1));
      }
      if (res.statusCode !== 200) { res.resume(); return reject(new Error(`Release download returned HTTP ${res.statusCode}`)); }
      resolve(res);
    });
    req.on('timeout', () => req.destroy(new Error('Update request timed out')));
    req.on('error', reject);
  });
}

async function releaseList() {
  const res = await request(API);
  let body = '';
  for await (const chunk of res) {
    body += chunk;
    if (body.length > 2 * 1024 * 1024) throw new Error('Release response is too large');
  }
  const value = JSON.parse(body);
  if (!Array.isArray(value)) throw new Error('Release response is invalid');
  return value;
}

function checksum(body, name) {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = String(body || '').match(new RegExp(`^([a-fA-F0-9]{64})\\s+${escaped}\\s*$`, 'm'));
  return match?.[1].toLowerCase() || null;
}

function candidate(releases, { platform, arch, builtAt, sourceRevision, channel = 'all' }) {
  const name = ASSETS[`${platform}-${arch}`];
  if (!name || !Number.isFinite(Date.parse(builtAt))) return null;
  return releases.filter(r => !r.draft && (channel === 'all' || (channel === 'stable' ? !r.prerelease : r.prerelease)))
    .map(r => {
      const asset = r.assets?.find(a => a.name === name);
      const digest = checksum(r.body, name);
      const published = Date.parse(r.published_at);
      if (!asset || !digest || !Number.isFinite(published) || published <= Date.parse(builtAt)) return null;
      const releaseSource = String(r.body || '').match(/Source commit: `([a-f0-9]{40})`/)?.[1];
      if (!releaseSource || releaseSource === sourceRevision) return null;
      if (!Number.isSafeInteger(asset.size) || asset.size <= 0 || asset.size > MAX_DOWNLOAD) return null;
      const url = asset.browser_download_url;
      try { if (!allowed(new URL(url))) return null; } catch { return null; }
      return { tag: String(r.tag_name || '').slice(0, 100), name, url, sha256: digest,
        publishedAt: r.published_at, prerelease: Boolean(r.prerelease), size: asset.size };
    }).filter(Boolean).sort((a, b) => Date.parse(b.publishedAt) - Date.parse(a.publishedAt))[0] || null;
}

async function download(update, onProgress = () => {}) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'verseview-update-'));
  const file = path.join(directory, update.name);
  try {
    const res = await request(update.url);
    const declared = Number(res.headers['content-length']);
    if (declared > MAX_DOWNLOAD) throw new Error('Update package is too large');
    const hash = crypto.createHash('sha256');
    let received = 0;
    let lastPercent = -1;
    await pipeline(res, new Transform({ transform(chunk, _encoding, callback) {
      try {
        received += chunk.length;
        if (received > MAX_DOWNLOAD) throw new Error('Update package is too large');
        hash.update(chunk);
        const percent = Math.min(99, Math.floor(received / update.size * 100));
        if (percent !== lastPercent) { lastPercent = percent; onProgress({ phase: 'downloading', percent }); }
        callback(null, chunk);
      } catch (error) { callback(error); }
    } }), fs.createWriteStream(file, { flags: 'wx', mode: 0o600 }));
    if (received !== update.size || hash.digest('hex') !== update.sha256) throw new Error('Update checksum or size did not match the release');
    onProgress({ phase: 'verified', percent: 100 });
    return { directory, file };
  } catch (error) { fs.rmSync(directory, { recursive: true, force: true }); throw error; }
}

function prepareMac(updateFile, executable, { relaunch = true } = {}) {
  const bundle = path.resolve(executable, '../../..');
  if (!bundle.endsWith('.app') || !fs.lstatSync(bundle).isDirectory()) throw new Error('Installed Mac app could not be identified');
  const parent = path.dirname(bundle);
  const staging = fs.mkdtempSync(path.join(parent, '.verseview-update-'));
  try {
    execFileSync('/usr/bin/ditto', ['-x', '-k', updateFile, staging], { timeout: 120000 });
    const staged = path.join(staging, 'VerseView Detector.app');
    const binary = path.join(staged, 'Contents', 'MacOS', 'VerseView Detector');
    if (!fs.existsSync(binary) || !fs.statSync(binary).isFile()) throw new Error('Update archive does not contain the complete Mac app');
    execFileSync('/usr/bin/codesign', ['--verify', '--deep', '--strict', staged], { timeout: 30000 });
    const backup = path.join(parent, '.VerseView Detector.previous.app');
    // Reaching another verified update means the previous installation launched.
    // Keep one rollback copy, replacing only the backup created by this updater.
    if (fs.existsSync(backup)) fs.rmSync(backup, { recursive: true, force: true });
    const script = path.join(path.dirname(updateFile), 'apply-update.sh');
    const quote = value => `'${value.replaceAll("'", "'\\''")}'`;
    const cleanup = path.basename(path.dirname(updateFile)).startsWith('verseview-update-')
      ? `rmdir ${quote(staging)} 2>/dev/null || true\n/bin/rm -f ${quote(updateFile)} ${quote(script)}\nrmdir ${quote(path.dirname(updateFile))} 2>/dev/null || true\n` : '';
    const body = `#!/bin/sh\nset -eu\nwhile kill -0 ${process.pid} 2>/dev/null; do sleep 1; done\nif [ -e ${quote(backup)} ]; then exit 1; fi\nmv ${quote(bundle)} ${quote(backup)}\nif ! mv ${quote(staged)} ${quote(bundle)}; then mv ${quote(backup)} ${quote(bundle)}; exit 1; fi\nif ! /usr/bin/codesign --verify --deep --strict ${quote(bundle)}; then mv ${quote(bundle)} ${quote(staged)}; mv ${quote(backup)} ${quote(bundle)}; exit 1; fi\n${relaunch ? `/usr/bin/open ${quote(bundle)}` : ':'}\n${cleanup}`;
    fs.writeFileSync(script, body, { mode: 0o700 });
    return { script, staging, backup };
  } catch (error) { fs.rmSync(staging, { recursive: true, force: true }); throw error; }
}

async function launchInstaller(file, executable, spawnInstaller = spawn) {
  const installDir = path.win32.dirname(executable);
  const child = spawnInstaller(file, ['/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART', `/DIR=${installDir}`],
    { detached: true, stdio: 'ignore', windowsHide: false });
  await new Promise((resolve, reject) => { child.once('spawn', resolve); child.once('error', reject); });
  child.unref();
}

module.exports = { API, ASSETS, candidate, releaseList, download, prepareMac, launchInstaller, checksum };
