'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
for (const directory of ['', 'src', 'scripts', 'tests']) {
  for (const name of fs.readdirSync(path.join(root, directory))) {
    if (/\.(c?js)$/.test(name)) execFileSync(process.execPath, ['--check', path.join(root, directory, name)], { stdio: 'inherit' });
  }
}
const html = fs.readFileSync(path.join(root, 'src', 'index.html'), 'utf8');
if (!html.includes("connect-src 'none'") || /<script[^>]*>\s*[^<\s]/.test(html)) {
  throw new Error('Preview must keep its offline CSP and external script files');
}
console.log('JavaScript syntax and offline page checks passed.');
