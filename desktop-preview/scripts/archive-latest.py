"""Preserve native bundle metadata, then verify an extracted CI deliverable."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import zipfile

root = Path(__file__).resolve().parents[1]
build = Path((root / 'out/latest.txt').read_text(encoding='utf-8').strip())
provenance = json.loads((build / 'provenance.json').read_text(encoding='utf-8'))
assert provenance['platform'] == sys.platform, 'Archive verification requires the native host'
output = root / 'out/deliverables'
output.mkdir(parents=True, exist_ok=True)
archive = output / (build.name + ('.zip' if os.name == 'nt' else '.tar.gz'))
if os.name == 'nt':
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as handle:
        for file in sorted(build.rglob('*')):
            if file.is_file(): handle.write(file, file.relative_to(build.parent))
else:
    # tar stores symlinks and executable modes; uploading a raw app loses them.
    with tarfile.open(archive, 'w:gz', dereference=False) as handle:
        handle.add(build, arcname=build.name)
with archive.open('rb') as handle:
    digest = hashlib.file_digest(handle, 'sha256').hexdigest()
(output / (archive.name + '.sha256')).write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
with tempfile.TemporaryDirectory(prefix='vv-archive-check-') as temporary:
    destination = Path(temporary)
    if os.name == 'nt':
        with zipfile.ZipFile(archive) as handle: handle.extractall(destination)
    else:
        with tarfile.open(archive) as handle: handle.extractall(destination, filter='data')
    extracted = destination / build.name
    for artifact in provenance['artifacts']:
        target = extracted / Path(artifact).name
        if sys.platform == 'darwin': target /= 'VerseView Desktop Preview.app'
        subprocess.run(['node', str(root/'scripts/verify-package.cjs'), str(target)], check=True)
        if sys.platform == 'darwin':
            subprocess.run(['codesign', '--verify', '--deep', '--strict', str(target)], check=True)
        resources = target / ('Contents/Resources' if sys.platform == 'darwin' else 'resources')
        subprocess.run([sys.executable, str(root/'scripts/smoke-backend.py'), '--backend', str(resources/'backend')], check=True)
report = {'result': 'PASS', 'archive': archive.name, 'sha256': digest,
          'buildId': build.name, 'platform': sys.platform, 'arch': provenance['arch'],
          'extractedRuntimeVerified': True, 'extractedFrozenStartupVerified': True,
          'microphoneOrPresentationStarted': False}
(output / (build.name + '-archive-verification.json')).write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report))
