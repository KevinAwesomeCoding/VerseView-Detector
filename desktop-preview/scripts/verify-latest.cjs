'use strict';
const fs = require('node:fs'), path = require('node:path'), { execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const latest = fs.readFileSync(path.join(root, 'out', 'latest.txt'), 'utf8').trim();
const build = JSON.parse(fs.readFileSync(path.join(latest, 'provenance.json')));
for (const artifact of build.artifacts) {
  const target = build.platform === 'darwin' ? path.join(artifact, `${build.runtimeManifest.productName}.app`) : artifact;
  execFileSync(process.execPath, [path.join(__dirname, 'verify-package.cjs'), target], { stdio: 'inherit' });
}
