'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { verify: verifyBackend } = require('./backend-integrity.cjs');

(async () => {
  const target = process.argv[2];
  if (!target) throw new Error('Pass the packaged .app path or Windows app directory');
  const resources = target.endsWith('.app') ? path.join(target, 'Contents', 'Resources') : path.join(target, 'resources');
  const archive = path.join(resources, 'app.asar');
  const { listPackage, extractFile } = await import('@electron/asar');
  // ASAR's directory lookup splits on the host's path.sep. Keep provenance
  // keys portable, but use native separators when reading archive entries.
  const read = relative => extractFile(archive, path.normalize(relative));
  const build = JSON.parse(read('build-info.json'));
  const files = listPackage(archive).filter(file => path.extname(file));
  const allowed = /^(src\/|main\.cjs$|preload\.cjs$|update-service\.cjs$|outline-output\.cjs$|outline-preload\.cjs$|appearance\.cjs$|appearance-preferences\.cjs$|theme-icons\.cjs$|backend-manager\.cjs$|engine-feed\.cjs$|engine-commands\.cjs$|session-export\.cjs$|launch-preferences\.cjs$|profile-transfer\.cjs$|package\.json$|build-info\.json$)/;
  for (const file of files) {
    const relative = file.replace(/^[/\\]+/, '').replaceAll('\\', '/');
    assert.match(relative, allowed, `Unexpected packaged file: ${relative}`);
    if (relative === 'build-info.json') continue;
    if (relative === 'package.json') {
      assert.deepEqual(JSON.parse(read(relative)), build.runtimeManifest);
      continue;
    }
    const digest = crypto.createHash('sha256').update(read(relative)).digest('hex');
    assert.equal(digest, build.sourceFiles[relative], `Packaged bytes differ: ${relative}`);
  }
  for (const required of ['main.cjs', 'preload.cjs', 'update-service.cjs', 'outline-output.cjs', 'outline-preload.cjs', 'src/outline.js', 'src/outline-display.html', 'src/outline-display.js', 'src/outline-display.css', 'appearance.cjs', 'appearance-preferences.cjs', 'theme-icons.cjs', 'backend-manager.cjs', 'engine-feed.cjs', 'engine-commands.cjs', 'session-export.cjs', 'launch-preferences.cjs', 'profile-transfer.cjs', 'src/notes.js', 'src/session-policy.js', 'src/session-setup.js', 'src/options-policy.js', 'src/connections.js', 'src/index.html', 'src/dashboard.js',
    'src/verse-tools.js', 'src/verse-tools.css', 'src/transcript-view.js', 'src/operator.js', 'src/consumer.js', 'src/cloud-policy.js', 'src/cloud-settings.js', 'src/settings-policy.js', 'src/settings.js', 'src/desktop.js', 'src/desktop.css', 'src/dashboard.css', 'src/vendor/lucide.min.js', 'src/vendor/lucide.LICENSE']) {
    assert.ok(read(required).length, required);
  }
  for (const theme of ['original', 'sage', 'midnight', 'glass', 'galaxy', 'aurora', 'ember']) {
    for (const extension of ['png', 'icns', 'ico']) assert.ok(read(`src/assets/icons/verseview-${theme}.${extension}`).length);
  }
  assert.equal(build.runtimeManifest.productName, 'VerseView Detector');
  if (target.endsWith('.app') && process.platform === 'darwin') {
    const { execFileSync } = require('node:child_process');
    const icon = execFileSync('plutil', ['-extract', 'CFBundleIconFile', 'raw', '-o', '-', path.join(target, 'Contents/Info.plist')], { encoding: 'utf8' }).trim();
    assert.deepEqual(fs.readFileSync(path.join(resources, icon)), read('src/assets/icons/verseview-original.icns'));
    for (const license of ['LICENSE', 'LICENSES.chromium.html']) assert.ok(fs.statSync(path.join(resources, 'licenses', license)).size);
  }
  if (build.backend) {
    const manifest = verifyBackend(path.join(resources, 'backend'), build.platform, build.arch);
    assert.deepEqual(manifest.sourceFiles, build.backend.sourceFiles);
  }
  console.log(JSON.stringify({ result: 'PASS', target: path.resolve(target), buildId: build.buildId,
    verifiedFiles: files.length, productionEngineIncluded: !!build.backend }, null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });
