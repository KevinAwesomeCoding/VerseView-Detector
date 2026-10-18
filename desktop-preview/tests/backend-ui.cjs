'use strict';
const { _electron } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict'), fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const root = path.resolve(__dirname, '..'), output = path.join(root, 'test-results');
fs.mkdirSync(output, { recursive: true });
(async () => {
  if (!process.env.PREVIEW_EXECUTABLE) throw new Error('Run this check against a packaged app with its native companion');
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'vv-owned-backend-ui-'));
  const source = path.join(directory, 'source'); fs.mkdirSync(source);
  const original = { language: 'English', stt_engine: 'deepgram', mic_index: 0, dual_stt_enabled: true,
    secondary_language: 'ml', secondary_stt_engine: 'sarvam', bible_translation: 'KJV',
    deepgram_api_key: 'SECRET-STT-KEY', sarvam_api_key: 'SECRET-SARVAM-KEY',
    confidence: .75, manual_confirm: true, verify: false, llm_enabled: false, auto_start: true, future_setting: { keep: true },
    remote_url: 'http://127.0.0.1:50010/control.html' };
  fs.writeFileSync(path.join(source, 'settings.json'), JSON.stringify(original));
  let application, backendProfile, childPid, sourceBackend, hiddenBackend;
  const errors = [], checks = [];
  const alive = pid => { try { process.kill(pid, 0); return true; } catch { return false; } };
  try {
    sourceBackend = fs.readFileSync(path.join(root, 'backend-build', 'latest.txt'), 'utf8').trim();
    assert.ok(sourceBackend.startsWith(path.join(root, 'backend-build') + path.sep));
    hiddenBackend = sourceBackend + '-hidden-for-verification';
    fs.renameSync(sourceBackend, hiddenBackend);
    application = await _electron.launch({ executablePath: process.env.PREVIEW_EXECUTABLE, args: [],
      env: { ...process.env, VV_PREVIEW_TEST_PROFILE: '1', VV_BACKEND_VERIFY: '1', VV_BACKEND_SOURCE_PROFILE: source,
        VV_OBSERVER_TEST_DIRECTORY: path.join(directory, 'external-empty') } });
    backendProfile = path.join(await application.evaluate(({ app }) => app.getPath('userData')), 'Backend');
    assert.match(backendProfile, /[/\\]QA[/\\]Backend$/);
    fs.rmSync(backendProfile, { recursive: true, force: true });
    const page = await application.firstWindow(); page.on('pageerror', error => errors.push(error.message));
    await page.evaluate(() => localStorage.clear()); await page.reload();
    await page.locator('#preview-mode').selectOption('observer');
    const app = page.locator('#preview-surface'), action = name => app.locator(`[data-engine-action="${name}"]`);
    const nav = label => app.getByRole('button', { name: label, exact: true }).filter({ visible: true }).click();
    await app.locator('[data-backend-action="launch"]').click();
    await page.waitForFunction(() => window.previewShell.getBackend().status === 'ready', { timeout: 30000 });
    await action('start').waitFor();
    const backend = await page.evaluate(() => window.previewShell.getBackend());
    childPid = backend.pid;
    assert.equal(backend.frozen, true); assert.equal(backend.guiImported, false); assert.equal(backend.verification, true);
    await page.waitForFunction(() => window.previewShell.getObserver().selected === window.previewShell.getObserver().session?.session_id);
    assert.equal(await page.evaluate(() => window.previewShell.getObserver().session.pid), childPid);
    await page.waitForTimeout(700);
    assert.equal(await page.evaluate(() => window.previewShell.getObserver().session.control.state), 'stopped');
    assert.equal(await page.evaluate(() => window.previewShell.getObserver().session.transcripts.length), 0);
    const copied = JSON.parse(fs.readFileSync(path.join(backendProfile, 'settings.json')));
    assert.equal(copied.deepgram_api_key, 'SECRET-STT-KEY'); assert.equal(copied.auto_start, true);
    assert.deepEqual(copied.future_setting, { keep: true });
    checks.push('Packaged dashboard launches its bundled frozen companion, without Python command or legacy GUI; copied auto-start stays stopped');
    await page.screenshot({ path: path.join(output, 'backend-ready.png') });
    await action('start').click();
    await page.waitForFunction(() => document.querySelector('.vv-output-ref')?.textContent === 'John 3:16');
    await page.waitForFunction(() => document.querySelector('[data-speech-stream="secondary"]')?.textContent.includes('യോഹന്നാൻ'));
    await page.waitForFunction(() => document.querySelector('.vv-output-ref')?.textContent === 'John 3:17');
    await action('approve').waitFor();
    const pending = await page.evaluate(() => window.previewShell.getObserver().session.control.pending[0]);
    await action('approve').click();
    await page.waitForFunction(id => window.previewShell.getObserver().session.delivery_events.some(event =>
      event.candidate_id === id && event.outcome === 'COMMAND_ACCEPTED'), pending.candidate_id);
    await page.waitForFunction(() => document.querySelector('.vv-output-ref')?.textContent === 'John 3:18');
    checks.push('Frozen companion runs actual configure/main/callback/confirmation/delivery code with mocked microphone/provider/controller; bilingual events and candidate IDs reach the app');
    await action('panic').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session.control.results.some(item => item.action === 'panic' && item.outcome === 'requested'));
    await nav('Settings'); await page.keyboard.press('Shift+Escape');
    await page.waitForFunction(() => window.previewShell.getObserver().session.control.results.filter(item => item.action === 'panic').length === 2);
    checks.push('Clear output and Shift+Escape reach the existing panic action from session/settings views, with fake presentation only');
    await nav('Live session'); await action('stop').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session.control.state === 'stopped');
    await nav('Settings');
    await page.locator('[data-detector-setting="bible_translation"]').selectOption('WEB');
    await page.locator('[data-save-settings]').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session.control.settings.values.bible_translation === 'WEB');
    assert.equal(JSON.parse(fs.readFileSync(path.join(backendProfile, 'settings.json'))).bible_translation, 'web');
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(source, 'settings.json'))), original);
    assert.equal((await page.content()).includes('SECRET-STT-KEY'), false);
    checks.push('Standalone settings save uses only the private preview profile and preserves credentials/unknown fields; original source unchanged');
    await page.screenshot({ path: path.join(output, 'backend-settings.png') });
    // Only this disposable QA profile is edited. Verification supplies a fixed
    // Sunday-noon clock; normal packaged recognition always uses local time.
    const schedulePath = path.join(backendProfile, 'settings.json');
    const scheduledSettings = { ...JSON.parse(fs.readFileSync(schedulePath)), smart_schedule: true,
      language: 'English', stt_engine: 'deepgram', secondary_stt_engine: 'sarvam' };
    fs.writeFileSync(schedulePath, JSON.stringify(scheduledSettings));
    await nav('Live session'); await action('start').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session.host?.notice.includes('supported primary language'));
    assert.equal(await page.evaluate(() => window.previewShell.getObserver().session.control.state), 'stopped');
    scheduledSettings.stt_engine = 'sarvam';
    fs.writeFileSync(schedulePath, JSON.stringify(scheduledSettings));
    await action('start').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session.config.streams.primary.language === 'ml' &&
      window.previewShell.getObserver().session.control?.state === 'running');
    const scheduled = await page.evaluate(() => window.previewShell.getObserver().session);
    assert.equal(scheduled.config.streams.secondary.language, 'en');
    assert.equal(scheduled.config.streams.secondary.provider, 'deepgram');
    assert.equal(scheduled.config.streams.secondary.enabled, true);
    assert.match(scheduled.host.notice, /Smart Schedule selected Malayalam with English secondary/);
    assert.deepEqual(JSON.parse(fs.readFileSync(schedulePath)), scheduledSettings);
    await page.screenshot({ path: path.join(output, 'backend-schedule.png') });
    await action('stop').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session.control.state === 'stopped');
    checks.push('Smart Schedule applies the fixed QA service clock only on explicit Start, rejects incompatible providers, configures Malayalam/English, and leaves saved choices intact');
    process.kill(childPid, 'SIGKILL');
    await page.waitForFunction(() => window.previewShell.getBackend().status === 'failed');
    await page.waitForFunction(() => document.querySelector('[data-connection-notice]')?.textContent.includes('feed unavailable'));
    assert.equal(await page.evaluate(() => window.previewShell.getBackend().pid), null);
    await app.locator('[data-backend-action="launch"]').click();
    await page.waitForFunction(() => window.previewShell.getBackend().status === 'ready');
    await page.waitForFunction(old => window.previewShell.getObserver().session?.pid !== old && window.previewShell.getObserver().connection === 'connected', childPid);
    const replacement = await page.evaluate(() => window.previewShell.getBackend());
    assert.notEqual(replacement.pid, childPid); childPid = replacement.pid;
    await page.waitForFunction(() => window.previewShell.getObserver().session?.control?.state === 'stopped');
    checks.push('Unexpected owned-child exit is visible and never automatically restarted; explicit relaunch selects its new PID and stays stopped');
    await nav('Live session');
    await action('discard_session').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session.control.recovery.status === 'none');
    await app.locator('[data-backend-action="close"]').click();
    await page.waitForFunction(() => document.querySelector('[data-connection-notice]')?.textContent.includes('feed unavailable'));
    assert.equal(await action('start').isEnabled(), false);
    assert.equal(alive(childPid), false);
    await page.screenshot({ path: path.join(output, 'backend-closed-status.png') });
    checks.push('Crash and explicit Close both remove the connected footer; closed/stale controls stay disabled');
    await app.locator('[data-backend-action="launch"]').click();
    await page.waitForFunction(() => window.previewShell.getBackend().status === 'ready');
    await page.waitForFunction(() => window.previewShell.getObserver().connection === 'connected' && window.previewShell.getObserver().session.control.state === 'stopped');
    childPid = await page.evaluate(() => window.previewShell.getBackend().pid);
    await page.waitForFunction(() => document.querySelector('[data-connection-notice]')?.textContent.includes('Bundled backend connected'));
    await nav('Live session'); await action('start').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session.control.state === 'running');
    const processInfo = await application.evaluate(({ app }) => ({ executable: process.execPath, packaged: app.isPackaged, resources: process.resourcesPath }));
    const environment = await page.evaluate(() => window.verseviewDesktop.environment());
    await application.close(); application = null;
    assert.equal(alive(childPid), false, 'Quitting the app must stop its owned backend');
    checks.push('Quitting the dashboard while the verification engine runs stops and reaps the owned companion');
    assert.deepEqual(errors, []);
    const report = { result: 'PASS', testedAt: new Date().toISOString(), processInfo, environment, backend, checks, errors,
      isolated: true, buildTreeHidden: true, microphoneSTT: 'DEFERRED — injected callback audio substitute, not spoken input',
      visibleVerseVIEW: 'DEFERRED — fake controller', windowsNativeBackend: 'NOT BUILT on this Mac', legacyFeatures: 'Compatibility gates retained; migration incomplete' };
    fs.writeFileSync(path.join(output, 'backend-ui-checks.json'), JSON.stringify(report, null, 2)+'\n');
    console.log(JSON.stringify(report, null, 2));
  } catch (error) {
    if (application) { const page = await application.firstWindow().catch(() => null);
      if (page) await page.screenshot({ path: path.join(output, 'backend-failure.png') }).catch(() => {}); }
    throw error;
  } finally {
    if (application) await application.close().catch(() => {});
    if (childPid && alive(childPid)) process.kill(childPid, 'SIGTERM');
    if (hiddenBackend && fs.existsSync(hiddenBackend)) fs.renameSync(hiddenBackend, sourceBackend);
    fs.rmSync(directory, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
