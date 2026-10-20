const enableDeveloper = require('./enable-developer.cjs');
'use strict';
// Actual packaged app relocation/update/rollback; only a synthetic QA profile.
const { _electron } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict'), fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const crypto = require('node:crypto'), { execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '..'), output = path.join(root, 'test-results');
fs.mkdirSync(output, { recursive: true });
function bundle(executable) {
  assert.ok(executable && path.isAbsolute(executable), 'Pass absolute packaged executable paths');
  return process.platform === 'darwin' ? path.resolve(executable, '../../..') : path.dirname(executable);
}
function binary(target) {
  return process.platform === 'darwin' ? path.join(target, 'Contents/MacOS/VerseView Desktop Preview') : path.join(target, 'VerseView Desktop Preview.exe');
}
function digest(file) { return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'); }
function inventory(directory) {
  const values = {};
  function visit(relative) {
    for (const entry of fs.readdirSync(path.join(directory, relative), { withFileTypes: true })) {
      const key = path.join(relative, entry.name), file = path.join(directory, key);
      if (entry.isDirectory()) visit(key);
      else values[key] = entry.isSymbolicLink() ? `link:${fs.readlinkSync(file)}` : digest(file);
    }
  }
  visit(''); return values;
}
(async () => {
  const current = bundle(process.env.PREVIEW_EXECUTABLE), previous = bundle(process.env.PREVIOUS_PREVIEW_EXECUTABLE);
  assert.notEqual(current, previous, 'Use two separately identified packaged versions');
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'vv-preview-install-'));
  const destination = path.join(directory, 'Applications with spaces', path.basename(current));
  const source = path.join(directory, 'source'), backup = path.join(directory, 'profile-before-update');
  fs.mkdirSync(path.join(source, 'credentials'), { recursive: true });
  const credentialSource = path.join(source, 'credentials/service-account.json');
  fs.writeFileSync(credentialSource, JSON.stringify({ type: 'service_account', project_id: 'SECRET-QA', private_key: 'SECRET-FAKE', client_email: 'qa@example.invalid' }));
  const original = { language: 'English', stt_engine: 'deepgram', deepgram_api_key: 'SECRET-READINESS',
    gcp_credentials_path: credentialSource, bible_translation: 'KJV', auto_start: true,
    manual_confirm: true, verify: false, llm_enabled: false, auto_save_notes: false, qa_bot_silence: true,
    future_setting: { keep: 'synthetic migration fixture' } };
  fs.writeFileSync(path.join(source, 'settings.json'), JSON.stringify(original));
  const originalSource = inventory(source), originalApp = inventory(current), previousApp = inventory(previous);
  let application, page, profile, ownsProfile = false;
  const children = [], stages = [], errors = [];
  const alive = pid => { try { process.kill(pid, 0); return true; } catch { return false; } };
  const settings = () => JSON.parse(fs.readFileSync(path.join(profile, 'settings.json')));
  async function launch(executable, label, first = false) {
    application = await _electron.launch({ executablePath: executable, args: [], env: { ...process.env,
      VV_PREVIEW_TEST_PROFILE: '1', VV_BACKEND_VERIFY: '1', VV_BACKEND_SOURCE_PROFILE: source,
      VV_OBSERVER_TEST_DIRECTORY: path.join(directory, 'empty-observer') } });
    profile = path.join(await application.evaluate(({ app }) => app.getPath('userData')), 'Backend');
    assert.match(profile, /[/\\]QA[/\\]Backend$/);
    if (first) { assert.equal(fs.existsSync(profile), false, 'Close and clean earlier synthetic QA runs first'); ownsProfile = true; }
    page = await application.firstWindow(); await enableDeveloper(page); page.on('pageerror', error => errors.push(error.message));
    await page.locator('#preview-mode').selectOption('observer');
    const surface = page.locator('#preview-surface');
    await surface.getByRole('button', { name: 'Settings', exact: true }).filter({ visible: true }).click();
    await surface.locator('[data-backend-action="launch"]').click();
    await page.waitForFunction(() => window.previewShell.getBackend().status === 'ready');
    await page.waitForFunction(() => window.previewShell.getObserver().session?.control?.state === 'stopped');
    const backend = await page.evaluate(() => window.previewShell.getBackend()); children.push(backend.pid);
    assert.equal(backend.frozen, true); assert.equal(backend.verification, true);
    assert.equal(await page.evaluate(() => window.previewShell.getObserver().session.transcripts.length), 0);
    const processInfo = await application.evaluate(({ app }) => ({ executable: process.execPath, packaged: app.isPackaged }));
    assert.equal(processInfo.packaged, true); assert.equal(fs.realpathSync(processInfo.executable), fs.realpathSync(executable));
    assert.equal((await page.content()).includes('SECRET-'), false);
    const environment = await page.evaluate(() => window.verseviewDesktop.environment());
    if (environment.version === require('../package.json').version) {
      assert.equal((await page.content()).includes('VERSEVIEW_OBSERVER=1'), false);
      assert.match(await surface.locator('[aria-label="Observer setup"]').textContent(), /Saved Bible translation: .*applies on Start/);
      assert.match(await surface.locator('.vv-feedback').textContent(), /Bundled backend connected/);
    }
    stages.push({ label, processInfo, environment, backendPid: backend.pid, recognition: 'stopped' });
  }
  async function close() {
    await application.close(); application = null;
    for (const pid of children) assert.equal(alive(pid), false, `Owned backend ${pid} must exit before copying/removing files`);
  }
  async function saveTranslation(value) {
    await page.locator('[data-detector-setting="bible_translation"]').selectOption(value);
    await page.locator('[data-save-settings]').click();
    await page.waitForFunction(expected => window.previewShell.getObserver().session.control.settings.values.bible_translation === expected, value);
    await page.waitForFunction(() => document.querySelector('[data-settings-status]')?.textContent.includes('Settings saved'));
  }
  try {
    await launch(binary(previous), 'previous packaged version / initial private migration', true);
    assert.equal(settings().deepgram_api_key, original.deepgram_api_key);
    assert.deepEqual(settings().future_setting, original.future_setting);
    const credential = settings().gcp_credentials_path;
    assert.equal(fs.realpathSync(path.dirname(credential)), fs.realpathSync(path.join(profile, 'credentials')));
    assert.equal(digest(credential), digest(credentialSource));
    await saveTranslation('WEB'); await close();
    fs.cpSync(profile, backup, { recursive: true, verbatimSymlinks: true });
    const savedBackup = inventory(backup); assert.deepEqual(inventory(profile), savedBackup);
    // A changed original source must not overwrite the preview on update.
    fs.writeFileSync(path.join(source, 'settings.json'), JSON.stringify({ ...original, bible_translation: 'NLT' }));
    const changedSource = inventory(source);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.cpSync(current, destination, { recursive: true, verbatimSymlinks: true });
    execFileSync(process.execPath, [path.join(root, 'scripts/verify-package.cjs'), destination], { stdio: 'pipe' });
    if (process.platform === 'darwin') execFileSync('codesign', ['--verify', '--deep', '--strict', destination]);
    await launch(binary(destination), 'relocated current package / upgrade existing preview profile');
    assert.notEqual(stages[0].environment.buildId, stages[1].environment.buildId);
    assert.equal(settings().bible_translation, 'web'); assert.equal(settings().gcp_credentials_path, credential);
    assert.deepEqual(settings().future_setting, original.future_setting);
    await saveTranslation('ASV'); await page.screenshot({ path: path.join(output, 'readiness-upgraded.png') }); await close();
    const updatedSettings = fs.readFileSync(path.join(profile, 'settings.json'));
    fs.rmSync(destination, { recursive: true }); // Portable uninstall removes the app only.
    assert.deepEqual(fs.readFileSync(path.join(profile, 'settings.json')), updatedSettings);
    fs.cpSync(current, destination, { recursive: true, verbatimSymlinks: true });
    await launch(binary(destination), 'reinstall current package / retained preview data');
    assert.equal(settings().bible_translation, 'asv'); assert.equal(settings().gcp_credentials_path, credential); await close();
    await launch(binary(previous), 'previous package / read existing newer profile');
    assert.equal(settings().bible_translation, 'asv'); assert.deepEqual(settings().future_setting, original.future_setting); await close();
    fs.rmSync(profile, { recursive: true }); fs.cpSync(backup, profile, { recursive: true, verbatimSymlinks: true });
    assert.deepEqual(inventory(profile), savedBackup);
    await launch(binary(previous), 'rollback package plus complete pre-update profile backup');
    assert.equal(settings().bible_translation, 'web'); assert.equal(digest(settings().gcp_credentials_path), digest(credentialSource)); await close();
    assert.deepEqual(inventory(current), originalApp); assert.deepEqual(inventory(previous), previousApp);
    assert.deepEqual(inventory(source), changedSource); assert.equal(originalSource['credentials/service-account.json'], changedSource['credentials/service-account.json']);
    assert.deepEqual(errors, []);
    const report = { result: 'PASS', testedAt: new Date().toISOString(), platform: process.platform, stages,
      checks: ['Managed credentials/unknown settings copied privately once; saved auto-start never starts recognition',
        'Relocated package with spaces launches its own frozen companion and upgrades the existing preview profile without recopying source',
        'App-only portable uninstall preserves profile; reinstall retains changes and credentials',
        'Prior package reads this tested newer profile; restoring the complete stopped-state backup restores pre-update settings and credentials',
        'Both original packaged artifacts and source credentials remain unchanged; all owned children exit'],
      packagedArtifactsUnchanged: true, disposableTargetOnly: true, errors,
      microphoneSTT: 'NOT USED', visibleVerseVIEW: 'NOT USED', systemInstallerGatekeeperSmartScreen: 'UNVERIFIED',
      windowsGUI: process.platform === 'win32' ? 'Only this automated QA lifecycle' : 'UNVERIFIED on this Mac' };
    fs.writeFileSync(path.join(output, 'readiness-ui-checks.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify(report, null, 2));
  } catch (error) {
    if (page) await page.screenshot({ path: path.join(output, 'readiness-failure.png') }).catch(() => {});
    fs.writeFileSync(path.join(output, 'readiness-failure.json'), JSON.stringify({ error: error.message, stages }, null, 2));
    throw error;
  } finally {
    if (application) await application.close().catch(() => {});
    for (const pid of children) if (alive(pid)) process.kill(pid, 'SIGTERM');
    if (ownsProfile && profile && children.every(pid => !alive(pid))) fs.rmSync(profile, { recursive: true, force: true });
    fs.rmSync(directory, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
