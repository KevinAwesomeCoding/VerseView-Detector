"""Stage only the three verified native packages for an automated beta release."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

DOWNLOAD_NAMES = {
    ('win32', 'x64'): 'VerseView-Detector-Windows-Setup.exe',
    ('darwin', 'arm64'): 'VerseView-Detector-Mac-Apple-Silicon.zip',
    ('darwin', 'x64'): 'VerseView-Detector-Mac-Intel.zip',
}
EXPECTED = set(DOWNLOAD_NAMES)


def changes_since_previous_release(repo):
    try:
        tag = subprocess.run(
            ['git', 'describe', '--tags', '--match', 'desktop-beta-*', '--abbrev=0'],
            cwd=repo, capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
        subjects = subprocess.run(
            ['git', 'log', '--first-parent', '--format=%s', f'{tag}..HEAD'],
            cwd=repo, capture_output=True, text=True, check=True, timeout=10,
        ).stdout.splitlines()
        return [subject[:160] for subject in subjects if subject.strip()][:15]
    except (OSError, subprocess.SubprocessError):
        return []


def release_notes(checksums, source_commit=None, changes=()):
    lines = [
        '## Download VerseView Detector', '',
        'Choose the download for your computer under **Assets** below.', '',
        '| Computer | App download |', '| --- | --- |',
        f"| Windows 64-bit | `{DOWNLOAD_NAMES[('win32', 'x64')]}` |",
        f"| Mac with Apple Silicon (M-series) | `{DOWNLOAD_NAMES[('darwin', 'arm64')]}` |",
        f"| Mac with an Intel processor | `{DOWNLOAD_NAMES[('darwin', 'x64')]}` |", '',
        'Mac: extract the ZIP and move VerseView Detector.app to Applications. Windows: run Setup.exe to install for your user.', '',
        '**Beta:** final native visual checks and real microphone/STT-to-visible-VerseVIEW acceptance',
        'are deferred by the owner for later testing. Native Windows, Intel Mac and Apple Silicon build checks run before publication.',
        'Paid publisher signing/notarization is intentionally omitted. The original intermittent delivery incident remains unresolved.', '',
        "## What's new", '',
        *([f'- {change}' for change in changes] if changes else ['Detailed changes are available in the full changelog.']), '',
        '<details>', '<summary>Technical details and SHA256 checksums</summary>', '',
    ]
    if source_commit:
        lines += [f'Source commit: `{source_commit}`', '']
    lines += ['Build verification reports are retained with the GitHub Actions artifacts.', '', '```text']
    lines += [f'{digest}  {name}' for name, digest in sorted(checksums.items())]
    lines += ['```', '', '</details>', '']
    return '\n'.join(lines)


def prepare_artifacts(artifacts, output, source_commit=None, changes=None):
    artifacts, output = Path(artifacts), Path(output)
    staged, seen, filenames = [], set(), set()
    for report in sorted(artifacts.rglob('*-archive-verification.json')):
        data = json.loads(report.read_text(encoding='utf-8'))
        target = (data.get('platform'), data.get('arch'))
        if target not in EXPECTED or target in seen:
            raise ValueError('Unexpected or duplicate native build')
        if data.get('result') != 'PASS' or any(data.get(k) is not True for k in
                ('extractedRuntimeVerified', 'extractedFrozenStartupVerified')):
            raise ValueError('Native package did not pass extracted-runtime verification')
        required = ('installerRuntimeVerified', 'installerUninstallVerified') if target[0] == 'win32' else ('singleAppBundleVerified',)
        if any(data.get(key) is not True for key in required):
            raise ValueError('Consumer download verification is incomplete')
        name = data.get('archive')
        if not isinstance(name, str) or not name or '/' in name or '\\' in name or name in ('.', '..'):
            raise ValueError('Invalid package filename')
        if not name.endswith('.exe' if target[0] == 'win32' else '.zip'):
            raise ValueError('Unexpected package format')
        names = {name, name + '.sha256', report.name}
        if names & filenames:
            raise ValueError('Duplicate release filenames would overwrite another platform')
        filenames.update(names)
        package = report.parent / name
        with package.open('rb') as handle:
            digest = hashlib.file_digest(handle, 'sha256').hexdigest()
        if digest != data.get('sha256'):
            raise ValueError('Native package checksum differs from its verification report')
        seen.add(target)
        staged.append((DOWNLOAD_NAMES[target], package, digest))
    if seen != EXPECTED:
        raise ValueError('All three native builds must pass before publishing')
    # Validate every report before creating any release output.
    if output.exists():
        raise ValueError('Release staging directory must be new')
    output.mkdir(parents=True)
    for name, package, digest in staged:
        shutil.copy2(package, output / name)
    (output / 'release-notes.md').write_text(
        release_notes({name: digest for name, _, digest in staged}, source_commit,
                      changes_since_previous_release(Path.cwd()) if changes is None else changes), encoding='utf-8')
    return len(staged)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifacts', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--source-commit')
    args = parser.parse_args()
    count = prepare_artifacts(args.artifacts, args.output, args.source_commit)
    print(f'Verified and staged {count} native packages for the beta release.')
