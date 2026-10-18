'use strict';
const fs = require('node:fs'), path = require('node:path'), { execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const backend = fs.readFileSync(path.join(root, 'backend-build', 'latest.txt'), 'utf8').trim();
execFileSync(process.execPath, [path.join(__dirname, 'prepare.cjs')], { stdio: 'inherit' });
execFileSync(process.execPath, [path.join(__dirname, 'package.cjs'), ...process.argv.slice(2), `--backend=${backend}`], { stdio: 'inherit', cwd: root });
