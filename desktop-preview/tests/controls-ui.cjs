const enableDeveloper = require('./enable-developer.cjs');
'use strict';
const { _electron } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const readline = require('node:readline');
const root = path.resolve(__dirname, '..'), output = path.join(root, 'test-results');
fs.mkdirSync(output, { recursive: true });
(async () => {
  if (!process.env.OBSERVER_PYTHON) throw new Error('Set OBSERVER_PYTHON to the approved detector environment');
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'vv-controls-ui-'));
  const errors = [], checks = [];
  let application, fixture;
  try {
    fixture = spawn(process.env.OBSERVER_PYTHON, [path.join(__dirname, 'control_engine.py'), '--directory', directory],
      { cwd: path.resolve(root, '..'), stdio: ['pipe', 'pipe', 'pipe'] });
    let stderr = '';
    fixture.stderr.on('data', data => { stderr = (stderr + data).slice(-5000); });
    const lines = readline.createInterface({ input: fixture.stdout });
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(`Fixture startup failed: ${stderr}`)), 15000);
      fixture.once('error', reject);
      fixture.once('exit', code => { clearTimeout(timer); reject(new Error(`Fixture exited ${code}: ${stderr}`)); });
      lines.on('line', line => { try { if (JSON.parse(line).ready) { clearTimeout(timer); resolve(); } } catch {} });
    });
    application = await _electron.launch({ executablePath: process.env.PREVIEW_EXECUTABLE || require('electron'),
      args: process.env.PREVIEW_EXECUTABLE ? [] : [root],
      env: { ...process.env, VV_PREVIEW_TEST_PROFILE: '1', VV_OBSERVER_TEST_DIRECTORY: directory } });
    const page = await application.firstWindow(); await enableDeveloper(page);
    page.on('pageerror', error => errors.push(error.message));
    await page.evaluate(() => localStorage.clear()); await page.reload();
    await page.locator('#preview-mode').selectOption('observer');
    const app = page.locator('#preview-surface');
    const action = value => app.locator(`[data-engine-action="${value}"]`);
    await action('start').waitFor();
    assert.equal(await action('start').isEnabled(), true);
    assert.equal(await action('stop').isEnabled(), false);
    const original = await page.evaluate(() => window.previewShell.getObserver().session.session_id);
    await page.evaluate(id => window.verseviewDesktop.selectObserver(id), original);
    await action('start').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session?.control?.state === 'running');
    await page.waitForFunction(() => document.querySelector('[data-engine-action="stop"]')?.disabled === false);
    const running = await page.evaluate(() => window.previewShell.getObserver());
    assert.notEqual(running.session.session_id, original);
    assert.equal(running.selected, running.session.session_id);
    checks.push('Start reaches the backend; mocked lifecycle and selected-session rotation are acknowledged');
    const otherSession = 'f'.repeat(32), otherFile = path.join(directory, `engine-${running.session.pid + 1000000}.json`);
    fs.writeFileSync(otherFile, JSON.stringify({ ...running.session, pid: running.session.pid + 1000000,
      session_id: otherSession, control: { ...running.session.control, id: 'e'.repeat(32), results: [] } }));
    await page.waitForFunction(() => window.previewShell.getObserver().sources.length === 2);
    await page.evaluate(id => window.verseviewDesktop.selectObserver(id), otherSession);
    await page.waitForFunction(() => document.querySelector('[data-command-status]')?.textContent.includes('Start uses'));
    await page.evaluate(id => window.verseviewDesktop.selectObserver(id), running.session.session_id);
    fs.unlinkSync(otherFile);
    checks.push('Command feedback belongs to its host and clears when a different process is selected');

    await assert.rejects(page.evaluate(id => window.verseviewDesktop.stopEngine(id), original));
    fixture.stdin.write('hold\n');
    await action('approve').waitFor();
    const held = await page.evaluate(() => window.previewShell.getObserver().session.control.pending[0]);
    assert.equal(held.reference, 'John 3:18');
    assert.match(await app.locator('.vv-pending-candidate').textContent(), new RegExp(held.candidate_id));
    assert.match(await app.locator('.vv-output-ref').textContent(), /No accepted/);
    await page.screenshot({ path: path.join(output, 'controls-held.png') });
    await action('approve').click();
    await page.waitForFunction(id => window.previewShell.getObserver().session?.delivery_events.some(event =>
      event.candidate_id === id && event.outcome === 'COMMAND_ACCEPTED'), held.candidate_id);
    await page.waitForFunction(() => document.querySelector('.vv-output-ref')?.textContent === 'John 3:18');
    assert.equal(await action('approve').count(), 0);
    await assert.rejects(page.evaluate(({ sessionId, candidateId }) => window.verseviewDesktop.resolveCandidate(sessionId, candidateId, true),
      { sessionId: running.session.session_id, candidateId: held.candidate_id }));
    checks.push('Approval reaches the real confirmation/delivery gate with a fake browser, retaining candidate ID; repeat rejected');
    fixture.stdin.write('reject\n');
    await action('reject').waitFor();
    const rejected = await page.evaluate(() => window.previewShell.getObserver().session.control.pending[0].candidate_id);
    await action('reject').click();
    await page.waitForFunction(id => window.previewShell.getObserver().session?.delivery_events.some(event =>
      event.candidate_id === id && event.outcome === 'CANCELLED'), rejected);
    assert.equal(await app.locator('.vv-output-ref').textContent(), 'John 3:18');
    fixture.stdin.write('speech\n');
    await page.waitForFunction(() => document.querySelector('[data-speech-stream="primary"]')?.textContent.includes('John 3:20'));
    await page.waitForFunction(() => document.querySelector('.vv-output-ref')?.textContent === 'John 3:20');
    checks.push('Reject cancels its candidate; subsequent transcript callbacks continue updating speech/output');
    await page.screenshot({ path: path.join(output, 'controls-accepted.png') });
    let layoutCases = 0;
    for (const width of [1180, 900, 640]) {
      await application.evaluate(({ BrowserWindow }, size) => BrowserWindow.getAllWindows()[0].setSize(size, 650), width);
      for (const layout of ['studio', 'focus']) {
        await page.locator('#preview-layout').selectOption(layout);
        for (const theme of ['sage', 'midnight', 'glass', 'galaxy', 'aurora', 'ember']) {
          await app.locator('[data-setting="theme"]').selectOption(theme);
          await action('stop').scrollIntoViewIfNeeded();
          const bounds = await app.evaluate(surface => ({ client: surface.clientWidth, scroll: surface.scrollWidth }));
          assert.ok(bounds.scroll <= bounds.client + 1, JSON.stringify({ width, layout, theme, bounds }));
          assert.equal(await action('stop').isEnabled(), true);
          layoutCases++;
        }
      }
    }
    checks.push(`${layoutCases} layout/theme cases fit and keep Stop accessible`);
    await page.screenshot({ path: path.join(output, 'controls-narrow.png') });
    await action('stop').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session?.control?.state === 'stopped');
    await page.waitForFunction(() => document.querySelector('[data-engine-action="start"]')?.disabled === false);
    checks.push('Stop reaches mocked lifecycle; Stopped status restores Start');
    await page.locator('#preview-mode').selectOption('samples');
    assert.equal(await action('start').count(), 0);
    await page.locator('#preview-mode').selectOption('observer');
    assert.equal(await action('start').count(), 1);
    await app.locator('[data-speech-stream="primary"] p[lang="en"]').evaluate(element => {
      const range = document.createRange(); range.selectNodeContents(element);
      const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
    });
    fixture.stdin.end('finish\n');
    await page.waitForFunction(() => window.previewShell.getObserver().connection === 'stale', { timeout: 15000 });
    assert.equal(await action('start').isEnabled(), false, 'Copying transcripts must not freeze command availability');
    assert.equal(await page.evaluate(() => window.getSelection().toString()), 'John 3:20');
    await page.evaluate(() => window.getSelection().removeAllRanges());
    await app.locator('[data-connection="stale"]').waitFor({ timeout: 15000 });
    assert.equal(await action('start').isEnabled(), false);
    assert.equal(await action('stop').isEnabled(), false);
    checks.push('Sample mode has no backend controls; stale/closed target disables commands even while transcript text is selected');
    const processInfo = await application.evaluate(({ app }) => ({ executable: process.execPath, packaged: app.isPackaged }));
    const environment = await page.evaluate(() => window.verseviewDesktop.environment());
    assert.deepEqual(errors, []);
    const report = { result: 'PASS', testedAt: new Date().toISOString(), processInfo, environment, checks, layoutCases, errors,
      lifecycle: 'MOCKED start/stop callbacks; production GUI/device lifecycle not executed',
      approval: 'REAL engine confirmation/delivery code with fake browser and blocked HTTP',
      microphoneSTT: 'DEFERRED — callback input only', visibleVerseVIEW: 'DEFERRED', windowsRuntime: 'UNVERIFIED on this Mac' };
    fs.writeFileSync(path.join(output, 'controls-ui-checks.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify(report, null, 2));
  } catch (error) {
    if (application) { const page = await application.firstWindow().catch(() => null);
      if (page) await page.screenshot({ path: path.join(output, 'controls-failure.png') }).catch(() => {}); }
    throw error;
  } finally {
    if (application) await application.close();
    if (fixture?.exitCode === null) { fixture.kill('SIGTERM'); await new Promise(resolve => { fixture.once('exit', resolve); setTimeout(resolve, 2000).unref(); }); }
    fs.rmSync(directory, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
