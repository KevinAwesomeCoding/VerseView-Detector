const enableDeveloper = require('./enable-developer.cjs');
'use strict';
const { _electron } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path'), readline = require('node:readline');
const root = path.resolve(__dirname, '..'), output = path.join(root, 'test-results');
fs.mkdirSync(output, { recursive: true });
(async () => {
  if (!process.env.OBSERVER_PYTHON) throw new Error('Set OBSERVER_PYTHON to the approved existing Python');
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'vv-settings-ui-'));
  let application, fixture, lines, stderr = '';
  const errors = [], checks = [];
  const executablePath = process.env.PREVIEW_EXECUTABLE || require('electron');
  async function launch() {
    application = await _electron.launch({ executablePath, args: process.env.PREVIEW_EXECUTABLE ? [] : [root],
      env: { ...process.env, VV_PREVIEW_TEST_PROFILE: '1', VV_OBSERVER_TEST_DIRECTORY: directory } });
    const page = await application.firstWindow(); await enableDeveloper(page);
    page.on('pageerror', error => errors.push(error.message));
    return page;
  }
  try {
    fixture = spawn(process.env.OBSERVER_PYTHON, [path.join(__dirname, 'control_engine.py'), '--directory', directory, '--settings'],
      { cwd: path.resolve(root, '..'), stdio: ['pipe', 'pipe', 'pipe'] });
    fixture.stderr.on('data', chunk => { stderr = (stderr + chunk).slice(-5000); });
    lines = readline.createInterface({ input: fixture.stdout });
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error(`Settings fixture startup failed: ${stderr}`)), 15000);
      fixture.once('error', reject);
      fixture.once('exit', code => { clearTimeout(timeout); reject(new Error(`Fixture exited ${code}: ${stderr}`)); });
      lines.on('line', line => { try { if (JSON.parse(line).ready) { clearTimeout(timeout); resolve(); } } catch {} });
    });
    let page = await launch();
    await page.evaluate(() => localStorage.clear()); await page.reload();
    await page.locator('#preview-mode').selectOption('observer');
    const field = key => page.locator(`[data-detector-setting="${key}"]`);
    const navSettings = () => page.locator('#preview-surface').getByRole('button', { name: 'Settings', exact: true }).filter({ visible: true }).click();
    await page.waitForFunction(() => !!window.previewShell.getObserver().session?.control?.settings);
    await navSettings();
    assert.equal(await field('mic_index').inputValue(), '0');
    assert.equal(await page.locator('[data-save-settings]').isEnabled(), false);
    const target = 'http://test-host.local:50010/control.html';
    await field('mic_index').selectOption('2');
    await field('language').selectOption('Malayalam');
    assert.equal(await field('stt_engine').inputValue(), 'sarvam');
    assert.equal(await field('stt_engine').locator('option[value="deepgram"]').count(), 0);
    await field('stt_engine').selectOption('gcp');
    await field('dual_stt_enabled').check();
    await field('secondary_language').selectOption('en');
    await field('secondary_stt_engine').selectOption('deepgram');
    await field('bible_translation').selectOption('WEB');
    await field('remote_url').fill('file:///tmp/invalid');
    assert.equal(await page.locator('[data-save-settings]').isEnabled(), false);
    await field('remote_url').fill(target);
    await field('remote_url').focus();
    const focusNode = await field('remote_url').elementHandle();
    fixture.stdin.write('noise\n');
    await page.waitForFunction(() => window.previewShell.getObserver().session?.transcripts.some(row => row.text === 'Isolated settings check'));
    assert.equal(await focusNode.evaluate(element => element === document.activeElement), true);
    assert.equal(await field('remote_url').inputValue(), target);
    assert.equal(await page.locator('[data-save-settings]').isEnabled(), true);
    await page.screenshot({ path: path.join(output, 'settings-draft.png') });
    await page.locator('[data-save-settings]').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session?.control?.settings?.values.mic_index === 2);
    await page.waitForFunction(() => document.querySelector('[data-settings-status]')?.textContent.includes('Settings saved'));
    const saved = await page.evaluate(() => window.previewShell.getObserver().session.control.settings.values);
    assert.equal(saved.language, 'Malayalam'); assert.equal(saved.stt_engine, 'gcp');
    assert.equal(saved.secondary_language, 'en'); assert.equal(saved.remote_url, target);
    checks.push('Typed stopped-engine settings save reaches the production GUI binding with fake widgets and temporary disk settings');
    checks.push('Language/provider choices, invalid URL blocking, and draft/focus preservation during incoming events');

    await field('bible_translation').selectOption('NLT');
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Failure mode did not arm')), 5000);
      const listener = line => { try { if (JSON.parse(line).event === 'fail-save-ready') { clearTimeout(timeout); lines.removeListener('line', listener); resolve(); } } catch {} };
      lines.on('line', listener); fixture.stdin.write('fail-save\n');
    });
    await page.locator('[data-save-settings]').click();
    await page.waitForFunction(() => document.querySelector('[data-settings-status]')?.textContent.includes('Previous values were retained'));
    assert.equal(await page.evaluate(() => window.previewShell.getObserver().session.control.settings.values.bible_translation), 'WEB');
    assert.equal(await field('bible_translation').inputValue(), 'NLT');
    await page.screenshot({ path: path.join(output, 'settings-save-failure.png') });
    await page.locator('[data-save-settings]').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session?.control?.settings?.values.bible_translation === 'NLT');
    checks.push('Failed disk save is visibly rejected, backend values roll back, and the unsaved draft can be explicitly saved again');

    await field('remote_url').fill('http://draft.invalid/control.html');
    fixture.stdin.write('external\n');
    await page.waitForFunction(() => document.querySelector('[data-settings-status]')?.textContent.includes('changed elsewhere'));
    assert.equal(await field('remote_url').inputValue(), 'http://draft.invalid/control.html');
    assert.equal(await page.locator('[data-save-settings]').isEnabled(), false);
    await page.screenshot({ path: path.join(output, 'settings-conflict.png') });
    await page.locator('[data-reload-settings]').click();
    assert.equal(await field('bible_translation').inputValue(), 'ASV');
    assert.equal(await field('remote_url').inputValue(), target);
    checks.push('External settings edit preserves the draft but disables Save until explicit reload');

    await page.evaluate(() => window.verseviewDesktop.startEngine(window.previewShell.getObserver().session.session_id));
    await page.waitForFunction(() => window.previewShell.getObserver().session?.control?.state === 'running');
    assert.equal(await field('mic_index').isEnabled(), false);
    await assert.rejects(page.evaluate(() => {
      const session = window.previewShell.getObserver().session;
      return window.verseviewDesktop.saveSettings(session.session_id, session.control.settings.revision, { mic_index: 0 });
    }));
    await page.evaluate(() => window.verseviewDesktop.stopEngine(window.previewShell.getObserver().session.session_id));
    await page.waitForFunction(() => window.previewShell.getObserver().session?.control?.state === 'stopped');
    await page.waitForFunction(() => !document.querySelector('[data-detector-setting="mic_index"]').disabled);
    checks.push('Running engine locks editing and rejects direct settings IPC; stopped status restores editing (mocked lifecycle)');

    let layoutCases = 0;
    for (const width of [1180, 900, 640]) {
      await application.evaluate(({ BrowserWindow }, size) => BrowserWindow.getAllWindows()[0].setSize(size, 650), width);
      for (const layout of ['studio', 'focus']) {
        await page.locator('#preview-layout').selectOption(layout);
        for (const theme of ['sage', 'midnight', 'glass', 'galaxy', 'aurora', 'ember']) {
          await page.locator('[data-setting="theme"]').selectOption(theme);
          await page.locator('[data-reload-settings]').scrollIntoViewIfNeeded();
          const bounds = await page.locator('#preview-surface').evaluate(surface => ({ client: surface.clientWidth, scroll: surface.scrollWidth }));
          assert.ok(bounds.scroll <= bounds.client + 1, JSON.stringify({ width, layout, theme, bounds }));
          assert.equal(await field('mic_index').inputValue(), '2'); layoutCases++;
        }
      }
    }
    await page.screenshot({ path: path.join(output, 'settings-narrow.png') });
    checks.push(`${layoutCases} settings size/layout/theme cases fit; fields and reload/save controls remain accessible by scrolling`);
    await page.locator('#preview-mode').selectOption('samples');
    assert.equal(await page.locator('[data-detector-setting]').count(), 0);
    await page.locator('#preview-mode').selectOption('observer');
    assert.equal(await field('mic_index').inputValue(), '2');
    const processInfo = await application.evaluate(({ app }) => ({ executable: process.execPath, packaged: app.isPackaged }));
    const environment = await page.evaluate(() => window.verseviewDesktop.environment());
    await application.close(); application = null;
    page = await launch();
    await page.waitForFunction(() => !!window.previewShell.getObserver().session?.control?.settings);
    await navSettings();
    assert.equal(await field('mic_index').inputValue(), '2');
    assert.equal(await field('remote_url').inputValue(), target);
    assert.equal(await page.locator('[data-save-settings]').isEnabled(), false);
    assert.equal((await page.content()).includes('private-key-never-export'), false);
    assert.equal(await page.evaluate(() => JSON.stringify(window.previewShell.getObserver()).includes('private-key-never-export')), false);
    checks.push('Saved settings survive dashboard restart; samples remain separate; fixture credentials never enter the renderer');
    await page.locator('.vv-detector-settings h2').evaluate(element => {
      const range = document.createRange(); range.selectNodeContents(element);
      const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
    });
    fixture.stdin.end('finish\n');
    await page.waitForFunction(() => window.previewShell.getObserver().connection === 'stale');
    assert.equal(await field('remote_url').isEnabled(), false);
    assert.equal(await page.evaluate(() => window.getSelection().toString()), 'Speech and VerseVIEW settings');
    await page.evaluate(() => window.getSelection().removeAllRanges());
    checks.push('Closed/stale backend disables editing even while settings text is selected');
    assert.deepEqual(errors, []);
    const report = { result: 'PASS', testedAt: new Date().toISOString(), processInfo, environment, checks, layoutCases, errors,
      backend: 'Production settings/GUI binding and atomic store; fake GUI widgets, synthetic devices, temporary settings file',
      lifecycle: 'MOCKED start/stop', microphoneSTT: 'DEFERRED', visibleVerseVIEW: 'DEFERRED', windowsRuntime: 'UNVERIFIED on this Mac' };
    fs.writeFileSync(path.join(output, 'settings-ui-checks.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify(report, null, 2));
  } catch (error) {
    if (application) { const page = await application.firstWindow().catch(() => null);
      if (page) await page.screenshot({ path: path.join(output, 'settings-failure.png') }).catch(() => {}); }
    throw error;
  } finally {
    if (application) await application.close();
    if (fixture?.exitCode === null) {
      if (!fixture.stdin.writableEnded) fixture.stdin.end('finish\n');
      await Promise.race([new Promise(resolve => fixture.once('exit', resolve)), new Promise(resolve => setTimeout(resolve, 2000))]);
      if (fixture.exitCode === null) fixture.kill('SIGTERM');
    }
    fs.rmSync(directory, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
