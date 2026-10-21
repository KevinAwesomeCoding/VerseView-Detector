"""Fail closed on incomplete/corrupt beta download sets; no live services."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('release_artifacts', Path(__file__).resolve().parents[1] / 'desktop-preview/scripts/prepare-release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseArtifactsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.artifacts = self.root / 'artifacts'
        self.output = self.root / 'release'
        self.reports = []
        for platform, arch in sorted(release.EXPECTED):
            folder = self.artifacts / f'{platform}-{arch}'
            folder.mkdir(parents=True)
            package = folder / (f'build-{platform}-{arch}' + ('.exe' if platform == 'win32' else '.zip'))
            package.write_bytes(f'{platform}/{arch} synthetic package'.encode())
            data = dict(result='PASS', platform=platform, arch=arch, archive=package.name,
                        sha256=hashlib.sha256(package.read_bytes()).hexdigest(),
                        extractedRuntimeVerified=True, extractedFrozenStartupVerified=True,
                        singleAppBundleVerified=True, installerRuntimeVerified=True, installerUninstallVerified=True)
            report = folder / f'build-{platform}-{arch}-archive-verification.json'
            report.write_text(json.dumps(data)); self.reports.append(report)

    def change(self, **values):
        p = self.reports[0]; data = json.loads(p.read_text()); data.update(values); p.write_text(json.dumps(data))

    def rejected(self):
        with self.assertRaises(ValueError):
            release.prepare_artifacts(self.artifacts, self.output)
        self.assertFalse(self.output.exists(), 'Invalid inputs must not stage partial release files')

    def test_all_verified_targets_publish_only_readable_download_names(self):
        (self.artifacts / 'private-test-log.txt').write_text('not a download')
        self.assertEqual(release.prepare_artifacts(self.artifacts, self.output), 3)
        self.assertEqual({p.name for p in self.output.iterdir()}, set(release.DOWNLOAD_NAMES.values()) | {'release-notes.md'})
        notes = (self.output / 'release-notes.md').read_text()
        self.assertIn('<details>', notes)
        for report in self.reports:
            data = json.loads(report.read_text())
            name = release.DOWNLOAD_NAMES[(data['platform'], data['arch'])]
            self.assertEqual(hashlib.sha256((self.output / name).read_bytes()).hexdigest(), data['sha256'])
            self.assertIn(data['sha256'] + '  ' + name, notes)

    def test_missing_platform_cannot_publish(self):
        self.reports[0].unlink(); self.rejected()

    def test_changed_bytes_cannot_publish(self):
        p = self.reports[0]; data = json.loads(p.read_text()); (p.parent / data['archive']).write_bytes(b'changed'); self.rejected()

    def test_unverified_or_wrong_target_cannot_publish(self):
        self.change(extractedFrozenStartupVerified=False); self.rejected()
        self.change(extractedFrozenStartupVerified=True, platform='linux'); self.rejected()

    def test_package_paths_cannot_escape_report_directory(self):
        self.change(archive='../another.zip'); self.rejected()

    def test_two_platforms_cannot_overwrite_the_same_download(self):
        for p in self.reports[:2]:
            data = json.loads(p.read_text())
            source = p.parent / data['archive']
            renamed = p.parent / 'duplicate.zip'
            source.rename(renamed); data['archive'] = renamed.name; p.write_text(json.dumps(data))
        self.rejected()

    def test_consumer_structure_verification_is_required(self):
        self.change(singleAppBundleVerified=False); self.rejected()

    def test_windows_install_and_uninstall_must_be_verified(self):
        p = next(p for p in self.reports if json.loads(p.read_text())['platform'] == 'win32')
        for field in ['installerRuntimeVerified', 'installerUninstallVerified']:
            data = json.loads(p.read_text()); data[field] = False; p.write_text(json.dumps(data))
            self.rejected()
            data[field] = True; p.write_text(json.dumps(data))
