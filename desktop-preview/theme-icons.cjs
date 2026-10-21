'use strict';
const path = require('node:path');
const fs = require('node:fs');
const { validTheme } = require('./appearance.cjs');

const iconDirectory = path.join(__dirname, 'src', 'assets', 'icons');
function loadICNS(file, nativeImage) {
  // Electron's image decoder supports PNG, not ICNS. Read the largest embedded
  // PNG representation from the native asset rather than relying on OS decoding.
  const bytes = fs.readFileSync(file);
  if (bytes.toString('ascii', 0, 4) !== 'icns' || bytes.readUInt32BE(4) !== bytes.length) {
    throw new Error('Invalid ICNS container');
  }
  let selected;
  for (let offset = 8; offset + 8 <= bytes.length;) {
    const length = bytes.readUInt32BE(offset + 4);
    if (length < 8 || offset + length > bytes.length) throw new Error('Invalid ICNS representation');
    const data = bytes.subarray(offset + 8, offset + length);
    if (data.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) {
      const image = nativeImage.createFromBuffer(data);
      if (!image.isEmpty() && (!selected || image.getSize().width > selected.getSize().width)) selected = image;
    }
    offset += length;
  }
  if (!selected) throw new Error('ICNS has no supported PNG representation');
  return selected;
}
function iconPath(theme, extension = 'png') {
  if ((!validTheme(theme) && theme !== 'original') || !['png', 'ico', 'icns'].includes(extension)) throw new Error('Invalid theme icon');
  return path.join(iconDirectory, `verseview-${theme}.${extension}`);
}

// Static native assets: independent of window vibrancy and accessibility policy.
function applyThemeIcon({ app, window, nativeImage, theme, platform = process.platform }) {
  const format = platform === 'darwin' ? 'icns' : platform === 'win32' ? 'ico' : 'png';
  let image;
  let loadedFormat = format;
  try {
    image = format === 'icns' ? loadICNS(iconPath(theme, format), nativeImage)
      : nativeImage.createFromPath(iconPath(theme, format));
  } catch { /* A missing/invalid native asset falls back to its lossless PNG. */ }
  if (!image || image.isEmpty()) {
    image = nativeImage.createFromPath(iconPath(theme));
    loadedFormat = 'png';
  }
  if (image.isEmpty()) throw new Error(`Could not load ${theme} icon`);
  if (platform === 'darwin') app.dock.setIcon(image);
  else if (window && !window.isDestroyed()) window.setIcon(image);
  return { theme, format: loadedFormat, target: platform === 'darwin' ? 'dock' : 'window' };
}

module.exports = { iconPath, applyThemeIcon, loadICNS };
