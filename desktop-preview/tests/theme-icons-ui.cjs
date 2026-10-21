'use strict';
// macOS integration: real Electron, native image decoding, Dock setter, saved startup.
const { _electron } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const root = path.resolve(__dirname, '..');
const themes = ['sage', 'midnight', 'galaxy', 'aurora', 'ember', 'glass'];
const output = path.join(root, 'test-results', 'theme-icons');
fs.mkdirSync(output, { recursive: true });

(async () => {
  assert.equal(process.platform, 'darwin', 'Run this Dock integration check on macOS');
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'verseview-icons-'));
  const errors = [], results = [];
  let application, page, profile;
  const tag = `icons-${Date.now()}`;
  async function launch() {
    application = await _electron.launch({
      executablePath: process.env.PREVIEW_EXECUTABLE || require('electron'),
      args: process.env.PREVIEW_EXECUTABLE ? [] : [root],
      env: { ...process.env, VV_PREVIEW_TEST_PROFILE: '1', VV_PREVIEW_TEST_PROFILE_TAG: tag, VV_OBSERVER_TEST_DIRECTORY: directory }
    });
    page = await application.firstWindow();
    page.on('pageerror', error => errors.push(error.message));
    await page.locator('.vv-brand-mark').first().waitFor();
    await page.waitForFunction(() => window.previewShell.getEnvironment().appearance?.nativeIcon);
  }
  async function check(theme, icon = theme) {
    await page.waitForFunction(({t, icon}) => {
      const a = window.previewShell.getEnvironment().appearance;
      return a?.theme === t && a.nativeIcon?.theme === icon && !a.nativeIcon.error;
    }, { t: theme, icon });
    const images = await page.locator('.vv-brand-mark').evaluateAll(nodes => nodes.map(n => ({
      source: n.getAttribute('src'), complete: n.complete, width: n.naturalWidth
    })));
    assert.ok(images.length >= 2, 'Both sidebar and narrow layout branding exist');
    for (const image of images) {
      assert.equal(image.source, `assets/icons/verseview-${icon}.png`);
      assert.ok(image.complete && image.width === 1024);
    }
    const appearance = await page.evaluate(() => window.previewShell.getEnvironment().appearance);
    assert.deepEqual(appearance.nativeIcon, { theme: icon, format: 'icns', target: 'dock' });
    assert.equal(appearance.mode, theme === 'glass' && !appearance.reducedTransparency && !appearance.highContrast ? 'native' : 'solid');
    return appearance;
  }
  try {
    await launch();
    profile = await application.evaluate(({ app }) => app.getPath('userData'));
    await check('glass', 'original');
    const originalLogo = await application.evaluate(({ app, nativeImage }) => {
      const image = nativeImage.createFromPath(`${app.getAppPath()}/src/assets/icons/verseview-original.png`);
      const bytes = image.toBitmap(), { width, height } = image.getSize();
      let left=width, right=-1, top=height, bottom=-1;
      for(let y=0;y<height;y++)for(let x=0;x<width;x++)if(bytes[(y*width+x)*4+3]>0){left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);}
      const original = app.dock.setIcon.bind(app.dock);
      globalThis.originalLogoPayload = null;
      app.dock.setIcon = image => {globalThis.originalLogoPayload=image.toPNG().toString('base64');return original(image);};
      return {left,right,top,bottom,width,height,corners:[bytes[3],bytes[(width-1)*4+3],bytes[(height-1)*width*4+3],bytes[bytes.length-1]],expected:image.toPNG().toString('base64')};
    });
    assert.ok(Math.abs((originalLogo.left+originalLogo.right+1)/2-originalLogo.width/2)<=1);
    assert.ok(Math.abs((originalLogo.top+originalLogo.bottom+1)/2-originalLogo.height/2)<=1);
    assert.deepEqual(originalLogo.corners,[0,0,0,0]);
    await page.evaluate(()=>window.verseviewDesktop.setTheme('glass',false));
    assert.equal(await application.evaluate(()=>globalThis.originalLogoPayload),originalLogo.expected);
    assert.equal(await application.evaluate(({ app }) => app.getName()), 'VerseView Detector');
    assert.equal(await application.evaluate(({ app }) => app.isPackaged), Boolean(process.env.PREVIEW_EXECUTABLE));
    await page.screenshot({ path: path.join(output, 'first-launch.png') });
    await application.close(); application = null;
    await launch();
    await check('glass', 'original');
    for (const theme of themes) {
      await application.evaluate(({ app }) => {
        const original = app.dock.setIcon.bind(app.dock);
        globalThis.iconCalls = [];
        app.dock.setIcon = image => { globalThis.iconCalls.push(image.toPNG().toString('base64')); return original(image); };
      });
      await page.getByRole('button', { name: 'Settings', exact: true }).filter({ visible: true }).click();
      await page.getByRole('button', { name: `${theme[0].toUpperCase()}${theme.slice(1)} theme`, exact: true }).click();
      const appearance = await check(theme);
      const dock = await application.evaluate(({ nativeImage, app }, t) => {
        const asset = `${app.getAppPath()}/src/assets/icons/verseview-${t}.png`;
        return { calls: globalThis.iconCalls, expected: nativeImage.createFromPath(asset).toPNG().toString('base64') };
      }, theme);
      // If the saved theme was already selected, force another choice before rechecking.
      if (!dock.calls.length) {
        const other = theme === 'sage' ? 'Ember' : 'Sage';
        await page.getByRole('button', { name: `${other} theme`, exact: true }).click();
        await page.getByRole('button', { name: `${theme[0].toUpperCase()}${theme.slice(1)} theme`, exact: true }).click();
        await check(theme);
        dock.calls = await application.evaluate(() => globalThis.iconCalls);
      }
      assert.equal(dock.calls.at(-1), dock.expected, 'Actual Dock setter received the correct decoded ICNS');
      await page.screenshot({ path: path.join(output, `${theme}.png`) });
      await application.close(); application = null;
      await launch();
      await check(theme);
      results.push({ theme, nativeFormat: appearance.nativeIcon.format, selection: 'passed', savedStartup: 'passed', backdrop: appearance.mode });
    }
    // Rapid changes must settle on the final theme, with no stale native icon.
    await page.getByRole('button', { name: 'Settings', exact: true }).filter({ visible: true }).click();
    await page.evaluate(() => {
      for (const theme of ['ember', 'glass', 'aurora', 'sage']) {
        document.querySelector(`[data-theme-choice="${theme}"]`).click();
      }
    });
    await check('sage');
    const final = await page.evaluate(() => window.verseviewDesktop.environment());
    assert.equal(final.appearance.nativeIcon.theme, 'sage');
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify({ centeredTransparentOriginal: 'passed', firstLaunchOriginal: 'passed', defaultRestartOriginal: 'passed', packaged: Boolean(process.env.PREVIEW_EXECUTABLE), executable: process.env.PREVIEW_EXECUTABLE || 'source', results, rapidChanges: 'passed', errors,
      windows: 'Deferred; no Windows graphical testing', dock: 'Real macOS native setter and ICNS decode verified; screenshots recorded separately' }, null, 2));
    console.log(JSON.stringify(results, null, 2));
  } finally {
    if (application) await application.close();
    if (profile) fs.rmSync(profile, { recursive: true, force: true });
    fs.rmSync(directory, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
