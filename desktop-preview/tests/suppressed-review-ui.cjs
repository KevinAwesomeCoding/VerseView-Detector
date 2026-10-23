'use strict';
const { _electron } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

(async () => {
  if (!process.env.PREVIEW_EXECUTABLE) throw new Error('Use the packaged application');
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'vv-suppressed-review-'));
  const source = path.join(temporary, 'source');
  fs.mkdirSync(source);
  fs.writeFileSync(path.join(source, 'settings.json'), JSON.stringify({
    language: 'English', stt_engine: 'deepgram', mic_index: 0,
    deepgram_api_key: 'SYNTHETIC', dual_stt_enabled: false,
    manual_confirm: false, verify: false, llm_enabled: false, auto_start: false,
    auto_save_notes: false, watcher_enabled: false, settings_sync_url: ''
  }));
  let application;
  try {
    application = await _electron.launch({ executablePath: process.env.PREVIEW_EXECUTABLE, args: [],
      env: { ...process.env, VV_PREVIEW_TEST_PROFILE: '1', VV_PREVIEW_TEST_PROFILE_TAG: `suppressed-review-${process.pid}`,
        VV_BACKEND_VERIFY: '1', VV_BACKEND_SOURCE_PROFILE: source,
        VV_OBSERVER_TEST_DIRECTORY: path.join(temporary, 'empty') } });
    const page = await application.firstWindow();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.locator('[data-consumer-prepare="settings"]').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session?.control?.state === 'stopped');
    await page.locator('[data-consumer-prepare="start"]').click();
    await page.waitForFunction(() => window.previewShell.getObserver().session?.control?.state === 'running');
    await page.evaluate(() => {
      window.previewShell.getObserver().session.delivery_events.push({
        candidate_id: 'test-suppressed-reference', reference: 'John 3:16', outcome: 'SUPPRESSED',
        reason: 'No book/chapter/verse anchor', timestamp: new Date().toISOString(),
        stream: 'primary', language: 'en', source: 'TEST', stage: 'delivery'
      });
      document.getElementById('verseview-prototype').dispatchEvent(new Event('preview:observer'));
    });
    const card = page.locator('.vv-suppressed-review');
    await card.waitFor();
    assert.match(await card.innerText(), /Detected John 3:16/);
    assert.match(await card.innerText(), /not displayed/);
    const sentBefore = await page.evaluate(() => window.previewShell.getObserver().session.delivery_events.filter(e => e.outcome === 'COMMAND_ACCEPTED' && e.reference === 'John 3:16').length);
    await card.getByRole('button', { name: 'Review verse' }).click();
    await page.waitForFunction(() => window.previewShell.getObserver().session?.control?.verses?.selected?.reference === 'John 3:16');
    assert.equal(await page.locator('.vv-verse-dialog').isVisible(), true);
    assert.equal(await page.evaluate(() => window.previewShell.getObserver().session.delivery_events.filter(e => e.outcome === 'COMMAND_ACCEPTED' && e.reference === 'John 3:16').length), sentBefore);
    await page.locator('.vv-verse-dialog [data-verse="close"]').click();
    await card.getByRole('button', { name: 'Dismiss' }).click();
    assert.equal(await card.count(), 0);
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ result: 'PASS', detected: true, previewedWithoutSending: true, dismissed: true }));
  } finally {
    if (application) await application.close();
    fs.rmSync(temporary, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
