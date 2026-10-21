"""Build consumer downloads, then verify the extracted/installed native runtime."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

root = Path(__file__).resolve().parents[1]
build = Path((root / 'out/latest.txt').read_text(encoding='utf-8').strip())
provenance = json.loads((build / 'provenance.json').read_text(encoding='utf-8'))
assert provenance['platform'] == sys.platform, 'Deliverable verification requires the native host'
assert len(provenance['artifacts']) == 1, 'Expected one native application'
product = provenance['runtimeManifest']['productName']
assert product == 'VerseView Detector', 'Consumer product name must be stable'
artifact = Path(provenance['artifacts'][0])
output = root / 'out/deliverables'
output.mkdir(parents=True, exist_ok=True)
report = {'result': 'PASS', 'buildId': build.name, 'platform': sys.platform, 'arch': provenance['arch'],
          'extractedRuntimeVerified': True, 'extractedFrozenStartupVerified': True,
          'microphoneOrPresentationStarted': False}


def verify_runtime(target):
    subprocess.run(['node', str(root/'scripts/verify-package.cjs'), str(target)], check=True)
    if sys.platform == 'darwin':
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(target)], check=True)
    resources = target / ('Contents/Resources' if sys.platform == 'darwin' else 'resources')
    subprocess.run([sys.executable, str(root/'scripts/smoke-backend.py'), '--backend', str(resources/'backend')], check=True)


if sys.platform == 'darwin':
    archive = output / (build.name + '.zip')
    bundle = artifact / (product + '.app')
    # ditto preserves framework symlinks/executable modes. Suppress metadata
    # sidecars so Archive Utility presents exactly one app, with no outer folder.
    subprocess.run(['ditto', '-c', '-k', '--norsrc', '--keepParent', str(bundle), str(archive)], check=True)
    with zipfile.ZipFile(archive) as handle:
        assert {name.split('/')[0] for name in handle.namelist()} == {bundle.name}, 'Unexpected visible download contents'
        for name in ['LICENSE', 'LICENSES.chromium.html']:
            assert f'{bundle.name}/Contents/Resources/licenses/{name}' in handle.namelist(), 'Required license missing'
    with tempfile.TemporaryDirectory(prefix='vv-download-check-') as temporary:
        subprocess.run(['ditto', '-x', '-k', str(archive), temporary], check=True)
        assert {p.name for p in Path(temporary).iterdir()} == {bundle.name}
        verify_runtime(Path(temporary) / bundle.name)
    report['singleAppBundleVerified'] = True
elif sys.platform == 'win32':
    # GitHub's native Windows image includes Inno Setup; never install a tool
    # implicitly or silently fall back to a loose-files ZIP.
    compiler = shutil.which('ISCC.exe')
    if not compiler:
        compiler = str(Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Inno Setup 6/ISCC.exe')
    if not Path(compiler).is_file():
        raise RuntimeError('Inno Setup is required on the Windows build host')
    stem = build.name + '-Setup'
    subprocess.run([compiler, '/Qp', f'/DBuildDir={artifact}', f'/DOutputDirectory={output}',
                    f'/DOutputName={stem}', f'/DAppVersion={provenance["runtimeManifest"]["version"]}',
                    f'/DAppIcon={root / "src/assets/icons/verseview-original.ico"}',
                    str(root/'scripts/windows-installer.iss')], check=True)
    archive = output / (stem + '.exe')
    with tempfile.TemporaryDirectory(prefix='vv-installer-check-') as temporary:
        target = Path(temporary) / product
        log = root / 'test-results/ci-installer.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(archive), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                        '/SP-', '/CURRENTUSER', f'/DIR={target}', f'/LOG={log}'], check=True, timeout=180)
        try:
            assert (target / (product + '.exe')).is_file(), 'Installed application missing'
            verify_runtime(target)
            report['installerRuntimeVerified'] = True
        finally:
            uninstaller = target / 'unins000.exe'
            assert uninstaller.is_file(), 'Uninstaller missing'
            subprocess.run([str(uninstaller), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                            f'/LOG={root / "test-results/ci-uninstaller.log"}'], check=True, timeout=90)
        assert not (target / (product + '.exe')).exists(), 'Uninstall left the application executable'
        assert not (target / 'resources/app.asar').exists(), 'Uninstall left runtime resources'
        report['installerUninstallVerified'] = True
else:
    raise RuntimeError('Unsupported consumer platform')
with archive.open('rb') as handle:
    digest = hashlib.file_digest(handle, 'sha256').hexdigest()
(output / (archive.name + '.sha256')).write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
report.update(archive=archive.name, sha256=digest)
(output / (build.name + '-archive-verification.json')).write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report))
