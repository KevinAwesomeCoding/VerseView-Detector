'use strict';
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
function inventory(root) {
  const files = {};
  function visit(directory) {
    for (const entry of fs.readdirSync(path.join(root, directory), { withFileTypes: true })) {
      const relative = path.join(directory, entry.name).replaceAll('\\', '/');
      if (relative === 'backend-manifest.json') continue;
      const file = path.join(root, relative);
      if (entry.isSymbolicLink()) files[relative] = { symlink: fs.readlinkSync(file) };
      else if (entry.isDirectory()) visit(relative);
      else files[relative] = { sha256: crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex') };
    }
  }
  visit(''); return files;
}
function relocateLinks(source, destination, manifest) {
  for (const [relative, value] of Object.entries(manifest.files)) {
    if (!value.symlink) continue;
    const target = path.resolve(source, path.dirname(relative), value.symlink);
    const inside = path.relative(source, target);
    if (inside === '..' || inside.startsWith(`..${path.sep}`) || path.isAbsolute(inside)) throw new Error('Backend symlink escapes its source');
    const file = path.join(destination, relative);
    fs.unlinkSync(file);
    fs.symlinkSync(path.relative(path.dirname(file), path.join(destination, inside)), file);
  }
}
function verify(root, platform, arch) {
  const value = JSON.parse(fs.readFileSync(path.join(root, 'backend-manifest.json'), 'utf8'));
  if (value.platform !== platform || value.arch !== arch) throw new Error('Native backend platform/architecture mismatch');
  if (JSON.stringify(Object.entries(inventory(root)).sort()) !== JSON.stringify(Object.entries(value.files).sort())) throw new Error('Backend file integrity mismatch');
  return value;
}
module.exports = { inventory, verify, relocateLinks };
