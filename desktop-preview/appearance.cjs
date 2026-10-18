'use strict';

// Native effects are a shell concern; the dashboard always has a solid fallback.
const THEMES = Object.freeze(['sage', 'midnight', 'glass', 'galaxy', 'aurora', 'ember']);
const DARK_THEMES = new Set(['midnight', 'galaxy', 'aurora']);
const validTheme = value => THEMES.includes(value);

function backdropPolicy({ platform, release, theme, reducedTransparency, highContrast }) {
  if (!validTheme(theme)) throw new TypeError('Unknown theme');
  if (theme !== 'glass') return { mode: 'solid', reason: 'Solid theme selected' };
  if (reducedTransparency || highContrast) {
    return { mode: 'solid', reason: 'System accessibility settings prefer solid surfaces' };
  }
  if (platform === 'darwin') return { mode: 'native', material: 'under-window', reason: 'macOS native glass' };
  // Electron system backdrop materials require Windows 11 22H2 (build 22621).
  const [major, , build] = String(release).split('.').map(Number);
  if (platform === 'win32' && major >= 10 && build >= 22621) {
    return { mode: 'native', material: 'acrylic', reason: 'Windows native acrylic' };
  }
  return { mode: 'solid', reason: 'Native glass is unavailable on this system' };
}

function backgroundColor(theme, dark) {
  return ({ midnight: '#111319', galaxy: '#141026', aurora: '#0d1e28' })[theme]
    || (theme === 'ember' ? (dark ? '#211812' : '#f7f1e9')
      : theme === 'glass' ? (dark ? '#121d2d' : '#dce7ef')
        : (dark ? '#111817' : '#f4f5f2'));
}

module.exports = { THEMES, DARK_THEMES, validTheme, backdropPolicy, backgroundColor };
