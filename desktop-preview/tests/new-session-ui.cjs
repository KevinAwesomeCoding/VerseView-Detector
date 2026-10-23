'use strict';
// Packaged app acceptance with synthetic recognition and a disposable profile.
const { _electron } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

(async () => {
  if (!process.env.PREVIEW_EXECUTABLE) throw new Error('Use the packaged application');
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'vv-new-session-ui-'));
  const source = path.join(temporary, 'source');
  fs.mkdirSync(source);
  fs.writeFileSync(path.join(source, 'settings.json'), JSON.stringify({
    language: 'English', stt_engine: 'deepgram', mic_index: 0,
    deepgram_api_key: 'SYNTHETIC', dual_stt_enabled: true,
    secondary_language: 'ml', secondary_stt_engine: 'sarvam', sarvam_api_key: 'SYNTHETIC',
    manual_confirm: true, verify: false, llm_enabled: false, auto_start: false,
    auto_save_notes: false, watcher_enabled: false, settings_sync_url: ''
  }));
  const tag = `new-session-${process.pid}`;
  let application;
  try {
    application = await _electron.launch({ executablePath: process.env.PREVIEW_EXECUTABLE, args: [],
      env: { ...process.env, VV_PREVIEW_TEST_PROFILE: '1', VV_PREVIEW_TEST_PROFILE_TAG: tag,
        VV_BACKEND_VERIFY: '1', VV_BACKEND_SOURCE_PROFILE: source,
        VV_OBSERVER_TEST_DIRECTORY: path.join(temporary, 'empty') } });
    const page = await application.firstWindow();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.locator('[data-consumer-prepare="settings"]').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session?.control?.state === 'stopped');
    await page.locator('[data-consumer-prepare="start"]').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session?.control?.state === 'running');
    const before = await page.evaluate(() => window.previewShell.getObserver().session.session_id);
    const stop = page.locator('[data-live-stop]').filter({ visible: true }).first();
    const fresh = page.locator('[data-new-session]').filter({ visible: true }).first();
    assert.equal(await stop.isEnabled(), true);
    assert.equal(await fresh.isEnabled(), true);
    await fresh.click();
    try {
      await page.waitForFunction(previous => window.previewShell.getObserver().session?.session_id !== previous,
        before, { timeout: 90000 });
    } catch (error) {
      console.error(JSON.stringify(await page.evaluate(() => ({
        state: window.previewShell.getObserver().session?.control?.state,
        actions: window.previewShell.getObserver().session?.control?.actions,
        results: window.previewShell.getObserver().session?.control?.results,
        operator: window.previewShell.getObserver().session?.control?.operator?.message,
        recovery: window.previewShell.getObserver().session?.control?.recovery,
        notes: window.previewShell.getObserver().session?.control?.notes,
        connections: window.previewShell.getObserver().session?.control?.connections,
        notice: document.querySelector('.vv-consumer-status')?.parentElement?.innerText
      })), null, 2));
      throw error;
    }
    const after = await page.evaluate(() => window.previewShell.getObserver().session);
    assert.equal(after.control.state, 'stopped');
    assert.equal(after.control.recovery.status, 'none');
    assert.equal(after.transcripts.length, 0);
    assert.equal(after.control.verses.history.length, 0);
    assert.ok(after.control.operator.library.rows.some(row => row.reason === 'before new session'));
    await page.waitForFunction(() => {
      const button = [...document.querySelectorAll('[data-consumer-prepare="start"]')].find(row => row.getClientRects().length);
      return button && !button.disabled;
    });
    await page.locator('[data-consumer-prepare="start"]').filter({ visible: true }).click();
    await page.waitForFunction(() => window.previewShell.getObserver().session?.control?.state === 'running');
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ result: 'PASS', savedSession: true, clearedContext: true, restarted: true }));
  } finally {
    if (application) await application.close();
    fs.rmSync(temporary, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
