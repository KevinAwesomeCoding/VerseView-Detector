'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { validTheme } = require('./appearance.cjs');

function loadAppearance(file) {
  try {
    const value = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (validTheme(value?.theme) && typeof value.themedIcon === 'boolean') return value;
  } catch { /* A missing or invalid preference leaves the original icon intact. */ }
  return { theme: 'glass', themedIcon: false };
}
function saveAppearance(file, value) {
  if (!validTheme(value?.theme) || typeof value.themedIcon !== 'boolean') throw new Error('Invalid appearance preference');
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = file + '.tmp';
  try {
    fs.writeFileSync(temporary, JSON.stringify({ theme: value.theme, themedIcon: value.themedIcon }), { mode: 0o600 });
    fs.renameSync(temporary, file);
  } finally { fs.rmSync(temporary, { force: true }); }
}
module.exports = { loadAppearance, saveAppearance };
