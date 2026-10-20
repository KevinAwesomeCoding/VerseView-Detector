const enableDeveloper = require('./enable-developer.cjs');
'use strict';
// Uses an existing Playwright installation; no browser download is needed.
const { _electron } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'test-results');
fs.mkdirSync(output, { recursive: true });

(async () => {
  const executablePath = process.env.PREVIEW_EXECUTABLE || require('electron');
  const args = process.env.PREVIEW_EXECUTABLE ? [] : [root];
  const errors = [], consoleErrors = [], checks = [];
  let application;
  const observerDirectory = fs.mkdtempSync(path.join(os.tmpdir(), 'verseview-sample-ui-'));
  async function launch() {
    application = await _electron.launch({ executablePath, args,
      env: { ...process.env, VV_PREVIEW_TEST_PROFILE: '1', VV_OBSERVER_TEST_DIRECTORY: observerDirectory } });
    const page = await application.firstWindow(); await enableDeveloper(page);
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
    await page.locator('.vv-output-ref').waitFor();
    return page;
  }
  try {
    let page = await launch();
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.locator('#preview-mode').selectOption('samples');
    const app = page.locator('#preview-surface');
    const nav = label => app.getByRole('button', { name: label, exact: true }).filter({ visible: true }).click();
    const reference = () => app.locator('.vv-output-ref').textContent();
    await page.waitForFunction(() => {
      const environment = window.previewShell.getEnvironment();
      return environment.platform !== 'browser' && environment.appearance?.theme === 'glass'
        && ['native', 'solid'].includes(environment.appearance?.mode);
    });
    const environment = await page.evaluate(() => window.verseviewDesktop.environment());
    const processInfo = await application.evaluate(({ app, BrowserWindow }) => ({
      executable: process.execPath, packaged: app.isPackaged, name: app.getName(), userData: app.getPath('userData'),
      preferences: BrowserWindow.getAllWindows()[0].webContents.getLastWebPreferences()
    }));
    assert.equal(processInfo.preferences.nodeIntegration, false);
    assert.equal(processInfo.preferences.contextIsolation, true);
    assert.equal(processInfo.preferences.sandbox, true);
    assert.match(processInfo.userData, /VerseView Desktop Preview[/\\]QA$/);
    assert.equal(await page.evaluate(() => typeof window.require), 'undefined');
    await assert.rejects(page.evaluate(() => window.verseviewDesktop.setTheme('invalid')));
    assert.equal(await page.evaluate(async () => {
      try { await fetch('http://127.0.0.1:50010/control.html'); return true; } catch { return false; }
    }), false);
    checks.push('Restricted renderer, invalid IPC rejected, and VerseVIEW network access blocked');
    // The deliberate CSP rejection above is expected; later console errors are not.
    consoleErrors.length = 0;
    assert.equal(await reference(), 'John 3:16');
    assert.equal(await app.locator('[data-speech-stream]').count(), 2);
    assert.equal(await app.locator('[data-action="run"],[data-action="run-both"]').count(), 0);
    await page.screenshot({ path: path.join(output, 'packaged-glass.png') });

    await nav('Test area');
    await app.locator('[data-action="run-both"]').click();
    await nav('Live session');
    assert.equal(await reference(), 'John 3:17');
    assert.match(await app.locator('[data-speech-stream="primary"] .vv-ref-notice').textContent(), /Command accepted/);
    assert.match(await app.locator('[data-speech-stream="secondary"] .vv-ref-notice').textContent(), /Duplicate/);
    await nav('Activity');
    assert.equal(await app.locator('.vv-activity-item').filter({ hasText: 'John 3:17 · Command accepted' }).count(), 1);
    checks.push('Separate bilingual samples, shared output, and cross-stream duplicate suppression');

    await nav('Test area');
    await app.locator('[data-setting="sample"][data-stream="secondary"]').selectOption('manual');
    await app.locator('[data-action="run"][data-stream="secondary"]').click();
    await nav('Live session');
    assert.equal(await reference(), 'John 3:17');
    await app.locator('[data-action="approve"]').click();
    assert.equal(await reference(), 'John 3:18');
    assert.match(await app.locator('.vv-output-status').textContent(), /Malayalam/);
    await nav('Test area');
    await app.locator('[data-setting="sample"][data-stream="secondary"]').selectOption('range');
    await app.locator('[data-action="run"][data-stream="secondary"]').click();
    await app.locator('[data-action="read-next"]').click();
    await nav('Live session');
    assert.equal(await reference(), 'John 3:20');
    checks.push('Sample approval and simulated queue release retain Malayalam attribution');

    for (const theme of ['sage', 'midnight', 'glass', 'galaxy', 'aurora', 'ember']) {
      await app.locator('[data-setting="theme"]').selectOption(theme);
      await page.waitForFunction(value => window.previewShell.getEnvironment().appearance?.theme === value, theme);
      assert.equal(await reference(), 'John 3:20');
      if (theme !== 'glass') assert.equal(await page.locator('#verseview-prototype').getAttribute('data-backdrop'), 'solid');
      await page.screenshot({ path: path.join(output, `theme-${theme}.png`) });
    }
    checks.push('Six themes switch native/solid appearance without resetting the sample session');

    let layoutCases = 0;
    for (const width of [1180, 900, 640]) {
      await application.evaluate(({ BrowserWindow }, width) => BrowserWindow.getAllWindows()[0].setSize(width, 650), width);
      for (const layout of ['studio', 'focus']) {
        await page.locator('#preview-layout').selectOption(layout);
        for (const view of ['Live session', 'Test area', 'Activity', 'Settings']) {
          await nav(view);
          const bounds = await app.evaluate(surface => ({ width: surface.clientWidth, scroll: surface.scrollWidth }));
          assert.ok(bounds.scroll <= bounds.width + 1, JSON.stringify({ width, layout, view, bounds }));
          layoutCases++;
        }
      }
    }
    await app.locator('[data-setting="theme"]').selectOption('galaxy');
    await app.locator('[aria-label="Desktop preview information"]').scrollIntoViewIfNeeded();
    const scrollState = await page.evaluate(() => {
      const titlebar = document.getElementById('preview-titlebar').getBoundingClientRect();
      const surface = document.getElementById('preview-surface');
      return { titlebarBottom: titlebar.bottom, contentTop: surface.getBoundingClientRect().top, scrollTop: surface.scrollTop };
    });
    assert.ok(scrollState.scrollTop > 0);
    assert.ok(scrollState.contentTop >= scrollState.titlebarBottom, 'Scrolled content must stay below native titlebar');
    await page.screenshot({ path: path.join(output, 'settings-scrolled.png') });
    await app.locator('[data-setting="threshold"]').focus();
    await page.keyboard.press('ArrowLeft');
    assert.equal(await app.locator('[data-setting="threshold"]').inputValue(), '89');
    await page.locator('#preview-reset').click();
    await nav('Live session');
    assert.equal(await reference(), 'John 3:16');
    assert.equal(await page.locator('#verseview-prototype').getAttribute('data-theme'), 'galaxy');
    checks.push(`${layoutCases} native-window layout checks, scrolling, keyboard input, and sample reset`);
    await application.close();
    application = null;
    page = await launch();
    assert.equal(await page.locator('#verseview-prototype').getAttribute('data-theme'), 'galaxy');
    assert.equal(await page.locator('#preview-layout').inputValue(), 'focus');
    assert.equal(await page.locator('.vv-output-ref').textContent(), 'John 3:16');
    checks.push('Theme/layout persist across app restart; sample session starts fresh');
    assert.deepEqual(errors, []);
    assert.deepEqual(consoleErrors, []);
    const report = { result: 'PASS', testedAt: new Date().toISOString(), environment, processInfo, checks,
      layoutCases, errors, consoleErrors, windowsRuntime: environment.platform === 'win32' ? 'PASS for sample UI on this Windows host' : 'UNVERIFIED on this Mac',
      microphoneAndDelivery: 'OUT OF SCOPE — samples only' };
    fs.writeFileSync(path.join(output, 'ui-checks.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify({ result: report.result, environment, checks }, null, 2));
  } catch (error) {
    if (application) {
      const page = await application.firstWindow().catch(() => null);
      if (page) await page.screenshot({ path: path.join(output, 'failure.png') }).catch(() => {});
    }
    throw error;
  } finally { if (application) await application.close(); fs.rmSync(observerDirectory, { recursive: true, force: true }); }
})().catch(error => { console.error(error); process.exitCode = 1; });
