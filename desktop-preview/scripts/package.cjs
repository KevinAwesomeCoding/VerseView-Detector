'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const { inventory, verify: verifyBackend, relocateLinks } = require('./backend-integrity.cjs');

(async () => {
  const root = path.resolve(__dirname, '..');
  const packageInfo = require('../package.json');
  const args = Object.fromEntries(process.argv.slice(2).map(value => value.replace(/^--/, '').split('=')));
  const platform = args.platform || process.platform;
  const arch = args.arch || process.arch;
  if (!['darwin', 'win32'].includes(platform) || !['arm64', 'x64'].includes(arch)) {
    throw new Error('Choose darwin/win32 and arm64/x64');
  }
  const backendPath = args.backend ? path.resolve(args.backend) : null;
  const backend = backendPath ? verifyBackend(backendPath, platform, arch) : null;
  const git = (...values) => execFileSync('git', values, { cwd: root, encoding: 'utf8' }).trim();
  const sourceRevision = git('rev-parse', 'HEAD');
  const builtAt = new Date().toISOString();
  const buildId = `${builtAt.replace(/[:.]/g, '-')}-${sourceRevision.slice(0, 8)}-${platform}-${arch}`;
  const files = {};
  function hashTree(directory) {
    for (const entry of fs.readdirSync(path.join(root, directory), { withFileTypes: true })) {
      if (['node_modules', 'out', 'backend-build', 'test-results', 'build-info.json'].includes(entry.name)) continue;
      const file = path.join(directory, entry.name).replaceAll('\\', '/');
      if (entry.isDirectory()) hashTree(file);
      else files[file] = crypto.createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex');
    }
  }
  hashTree('');
  // Packager intentionally removes development-only manifest fields.
  const runtimeManifest = { ...packageInfo };
  for (const key of ['private', 'scripts', 'devDependencies']) delete runtimeManifest[key];
  const provenance = { buildId, builtAt, sourceRevision, branch: git('branch', '--show-current'),
    workingTree: git('status', '--short', '--untracked-files=all'),
    command: `npm run package -- --platform=${platform} --arch=${arch}${backendPath ? ` --backend=${backendPath}` : ""}`, platform, arch,
    signing: platform === 'darwin' && process.platform === 'darwin' ? 'local ad-hoc test signing' : 'unsigned development artifact',
    backend: backend ? { sourceFiles: backend.sourceFiles, platform, arch, builtAt: backend.builtAt } : null,
    node: process.version, electron: packageInfo.devDependencies.electron,
    packager: packageInfo.devDependencies['@electron/packager'], runtimeManifest, sourceFiles: files };
  fs.writeFileSync(path.join(root, 'build-info.json'), JSON.stringify(provenance, null, 2) + '\n');
  const { packager } = await import('@electron/packager');
  const output = path.join(root, 'out', buildId);
  const artifacts = await packager({ dir: root, out: output, name: packageInfo.productName,
    icon: path.join(root, 'src', 'assets', 'icons', `verseview-original.${platform === 'darwin' ? 'icns' : 'ico'}`),
    ...(backendPath ? { extraResource: [backendPath] } : {}),
    ...(platform === 'darwin' ? { extendInfo: {
      NSMicrophoneUsageDescription: 'VerseView uses microphone audio when you explicitly start recognition.',
      NSUserNotificationAlertStyle: 'alert'
    } } : {}),
    appBundleId: 'com.verseview.detector.desktop-preview', appVersion: packageInfo.version,
    executableName: packageInfo.productName, platform, arch, asar: true, prune: true,
    // Explicit allowlist: never package the Python engine, production settings, or tests.
    ignore: file => {
      // Packager passes slash-prefixed paths relative to `dir` to this callback.
      const relative = file.replace(/^[/\\]+/, '');
      if (!relative) return false;
      return !['src', 'main.cjs', 'preload.cjs', 'update-service.cjs', 'outline-output.cjs', 'outline-preload.cjs', 'appearance.cjs', 'appearance-preferences.cjs', 'theme-icons.cjs', 'backend-manager.cjs', 'engine-feed.cjs', 'engine-commands.cjs', 'notification-actions.cjs', 'session-export.cjs', 'launch-preferences.cjs', 'profile-transfer.cjs', 'package.json', 'build-info.json'].includes(relative.split(/[/\\]/)[0]);
    }
  });
  if (platform === 'darwin' && process.platform === 'darwin') {
    for (const artifact of artifacts) {
      const bundle = path.join(artifact, `${packageInfo.productName}.app`);
      const licenses = path.join(bundle, 'Contents', 'Resources', 'licenses');
      fs.mkdirSync(licenses, { recursive: true });
      for (const name of ['LICENSE', 'LICENSES.chromium.html']) {
        fs.copyFileSync(path.join(artifact, name), path.join(licenses, name));
      }
      if (backend) relocateLinks(backendPath, path.join(bundle, 'Contents', 'Resources', 'backend'), backend);
      execFileSync('codesign', ['--force', '--deep', '--sign', '-',
        '--preserve-metadata=entitlements,requirements,flags,runtime', bundle], { stdio: 'inherit' });
      if (backend) {
        const packaged = path.join(bundle, 'Contents', 'Resources', 'backend');
        const manifestPath = path.join(packaged, 'backend-manifest.json');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        manifest.files = inventory(packaged);
        fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
        // Child signatures are already final; seal the updated manifest in the outer bundle.
        execFileSync('codesign', ['--force', '--sign', '-', '--preserve-metadata=entitlements,requirements,flags,runtime', bundle], { stdio: 'inherit' });
      }
      execFileSync('codesign', ['--verify', '--deep', '--strict', bundle], { stdio: 'inherit' });
    }
  }
  provenance.artifacts = artifacts;
  fs.writeFileSync(path.join(output, 'provenance.json'), JSON.stringify(provenance, null, 2) + '\n');
  fs.writeFileSync(path.join(root, 'out', 'latest.txt'), output + '\n');
  console.log(JSON.stringify({ buildId, artifacts, provenance: path.join(output, 'provenance.json') }, null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });
