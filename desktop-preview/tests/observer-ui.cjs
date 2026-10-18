'use strict';
const { _electron } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const readline = require('node:readline');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'test-results');
fs.mkdirSync(output, { recursive: true });

(async () => {
  if (!process.env.OBSERVER_PYTHON) throw new Error('Set OBSERVER_PYTHON to the existing detector Python environment');
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'vv-observer-integration-'));
  const executablePath = process.env.PREVIEW_EXECUTABLE || require('electron');
  const fixtures = [], errors = [], checks = [];
  let application;
  async function startFixture() {
    const child = spawn(process.env.OBSERVER_PYTHON, [path.join(__dirname, 'replay_engine.py'), '--directory', directory],
      { cwd: path.resolve(root, '..'), stdio: ['pipe', 'pipe', 'pipe'] });
    fixtures.push(child);
    let stderr = '';
    child.stderr.on('data', chunk => { stderr = (stderr + chunk).slice(-5000); });
    const lines = readline.createInterface({ input: child.stdout });
    const ready = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error(`Replay did not start: ${stderr}`)), 15000);
      child.once('error', error => { clearTimeout(timeout); reject(error); });
      child.once('exit', code => { clearTimeout(timeout); reject(new Error(`Replay exited ${code}: ${stderr}`)); });
      lines.on('line', line => {
        try { const value = JSON.parse(line); if (value.ready) { clearTimeout(timeout); resolve(value); } } catch { /* Non-protocol log. */ }
      });
    });
    return { child, ready };
  }
  try {
    application = await _electron.launch({ executablePath, args: process.env.PREVIEW_EXECUTABLE ? [] : [root],
      env: { ...process.env, VV_PREVIEW_TEST_PROFILE: '1', VV_OBSERVER_TEST_DIRECTORY: directory } });
    const page = await application.firstWindow();
    page.on('pageerror', error => errors.push(error.message));
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.locator('#preview-mode').selectOption('observer');
    const app = page.locator('#preview-surface');
    const nav = label => app.getByRole('button', { name: label, exact: true }).filter({ visible: true }).click();
    await app.locator('[data-connection="waiting"]').waitFor();
    assert.equal(await app.locator('[data-action="toggle"],[data-action="approve"],[data-action="run"]').count(), 0);
    assert.match(await app.locator('.vv-output-ref').textContent(), /No accepted command/);
    const first = await startFixture();
    await app.locator('[data-connection="connected"]').waitFor();
    await page.waitForFunction(() => document.querySelector('.vv-output-ref').textContent === 'John 3:16');
    assert.match(await app.locator('[data-speech-stream="primary"]').textContent(), /John 3:16/);
    assert.match(await app.locator('[data-speech-stream="secondary"]').textContent(), /യോഹന്നാൻ 3:16/);
    assert.match(await app.locator('.vv-observer-status').textContent(), /Callback replay · no microphone audio/);
    assert.match(await app.locator('.vv-output').textContent(), /Visible output unverified/);
    assert.equal(await app.locator('.vv-output .vv-verse').count(), 0, 'Do not substitute sample verse text for actual output');
    checks.push('Real engine callbacks reach the local feed and Electron, with raw Malayalam separate from translation');
    await page.screenshot({ path: path.join(output, 'observer-replay.png') });
    await nav('Activity');
    assert.ok((await app.locator('.vv-content').textContent()).includes(first.ready.accepted_id));
    assert.match(await app.locator('.vv-content').textContent(), /COMMAND_ACCEPTED/);
    assert.match(await app.locator('.vv-content').textContent(), /SUPPRESSED/);
    assert.match(await app.locator('.vv-content').textContent(), /secondary|Secondary/);
    checks.push('Candidate ID, outcome, stage, timestamp, language, and stream metadata retained');
    await nav('Test area');
    assert.equal(await app.locator('[data-action="run"],[data-action="approve"]').count(), 0);
    await app.locator('[data-action="sample-mode"]').click();
    await app.locator('[data-action="run-both"]').click();
    await nav('Live session');
    assert.equal(await app.locator('.vv-output-ref').textContent(), 'John 3:17');
    await page.locator('#preview-mode').selectOption('observer');
    assert.equal(await app.locator('.vv-output-ref').textContent(), 'John 3:16');
    const themeControl = await app.locator('[data-setting="theme"]').elementHandle();
    checks.push('Sample and observer states stay separate; no live approval or engine-control buttons');

    await app.locator('[data-speech-stream="secondary"] p[lang="ml"]').evaluate(element => {
      const range = document.createRange(); range.selectNodeContents(element);
      const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
    });
    first.child.stdin.write('advance\n');
    await page.waitForFunction(() => window.previewShell.getObserver().session?.delivery_events.some(event =>
      event.reference === 'John 3:17' && event.outcome === 'COMMAND_ACCEPTED'));
    assert.equal(await app.locator('.vv-output-ref').textContent(), 'John 3:16', 'Keep selected text stable during new events');
    await page.evaluate(() => window.getSelection().removeAllRanges());
    await page.waitForFunction(() => document.querySelector('.vv-output-ref').textContent === 'John 3:17');
    assert.equal(await themeControl.evaluate(element => element === document.querySelector('#preview-surface [data-setting="theme"]')), true,
      'Observer updates must preserve the actual theme control node');
    await nav('Activity');
    await app.getByText('MANUAL_CONFIRM_REQUIRED', { exact: false }).waitFor();
    assert.equal(await app.locator('[data-action="approve"]').count(), 0);
    checks.push('New engine events update the view; text selection is preserved; held John 3:18 never becomes accepted output');
    await page.screenshot({ path: path.join(output, 'observer-activity.png') });

    let layoutCases = 0;
    for (const width of [1180, 900, 640]) {
      await application.evaluate(({ BrowserWindow }, value) => BrowserWindow.getAllWindows()[0].setSize(value, 650), width);
      for (const layout of ['studio', 'focus']) {
        await page.locator('#preview-layout').selectOption(layout);
        for (const view of ['Live session', 'Activity', 'Test area', 'Settings']) {
          await nav(view);
          const bounds = await app.evaluate(surface => ({ client: surface.clientWidth, scroll: surface.scrollWidth }));
          assert.ok(bounds.scroll <= bounds.client + 1, JSON.stringify({ width, layout, view, bounds }));
          layoutCases++;
        }
      }
    }
    await application.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].setSize(1180, 880));
    await nav('Live session');
    for (const theme of ['sage', 'midnight', 'glass', 'galaxy', 'aurora', 'ember']) {
      await app.locator('[data-setting="theme"]').selectOption(theme);
      assert.equal(await app.locator('.vv-output-ref').textContent(), 'John 3:17');
    }
    checks.push(`${layoutCases} observer layout checks and six themes with event data retained`);

    first.child.stdin.end('finish\n');
    await app.locator('[data-connection="stale"]').waitFor({ timeout: 15000 });
    assert.equal(await app.locator('.vv-output-ref').textContent(), 'John 3:17');
    assert.match(await app.locator('.vv-observer-status').textContent(), /last snapshot/);
    await page.screenshot({ path: path.join(output, 'observer-stale.png') });
    const second = await startFixture();
    await app.locator('[data-connection="connected"]').waitFor();
    await page.waitForFunction(() => document.querySelector('.vv-output-ref').textContent === 'John 3:16');
    const snapshot = await page.evaluate(() => window.previewShell.getObserver());
    assert.equal(snapshot.session.pid, second.ready.pid);
    assert.equal(snapshot.session.delivery_events.some(event => event.reference === 'John 3:17'), false);
    checks.push('Heartbeat loss is visibly stale; a new source session replaces old transcripts and outcomes');
    await assert.rejects(page.evaluate(() => window.verseviewDesktop.selectObserver('../../settings.json')));
    await assert.rejects(page.evaluate(() => window.verseviewDesktop.startEngine(window.previewShell.getObserver().session.session_id)));
    assert.equal(await app.locator('[data-engine-action]').count(), 0);
    assert.equal(await page.evaluate(() => typeof window.verseviewDesktop.approve), 'undefined');
    const processInfo = await application.evaluate(({ app }) => ({ executable: process.execPath, packaged: app.isPackaged }));
    const environment = await page.evaluate(() => window.verseviewDesktop.environment());
    assert.deepEqual(errors, []);
    const report = { result: 'PASS', testedAt: new Date().toISOString(), environment, processInfo, checks, layoutCases,
      errors, session: snapshot.session.session_id, origin: snapshot.session.origin,
      microphoneSTTTransport: 'UNVERIFIED — callback replay, not spoken audio', windowsRuntime: 'UNVERIFIED on this Mac' };
    fs.writeFileSync(path.join(output, 'observer-ui-checks.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify({ result: report.result, environment, processInfo, checks }, null, 2));
  } catch (error) {
    if (application) {
      const page = await application.firstWindow().catch(() => null);
      if (page) await page.screenshot({ path: path.join(output, 'observer-failure.png') }).catch(() => {});
    }
    throw error;
  } finally {
    if (application) await application.close();
    for (const child of fixtures) {
      if (child.exitCode === null) {
        if (!child.stdin.writableEnded && !child.stdin.destroyed) child.stdin.end('finish\n');
        child.kill('SIGTERM');
        await new Promise(resolve => { child.once('exit', resolve); setTimeout(resolve, 2000).unref(); });
      }
    }
    fs.rmSync(directory, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
