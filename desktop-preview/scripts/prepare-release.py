"""Stage only the three verified native packages for an automated beta release."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

EXPECTED = {('win32', 'x64'), ('darwin', 'arm64'), ('darwin', 'x64')}


def prepare_artifacts(artifacts, output):
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
        name = data.get('archive')
        if not isinstance(name, str) or not name or '/' in name or '\\' in name or name in ('.', '..'):
            raise ValueError('Invalid package filename')
        if not name.endswith('.zip' if target[0] == 'win32' else '.tar.gz'):
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
        staged.append((report, package, digest))
    if seen != EXPECTED:
        raise ValueError('All three native builds must pass before publishing')
    # Validate every report before creating any release output.
    if output.exists():
        raise ValueError('Release staging directory must be new')
    output.mkdir(parents=True)
    for report, package, digest in staged:
        shutil.copy2(package, output / package.name)
        shutil.copy2(report, output / report.name)
        (output / (package.name + '.sha256')).write_text(f'{digest}  {package.name}\n', encoding='utf-8')
    return len(staged)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifacts', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    count = prepare_artifacts(args.artifacts, args.output)
    print(f'Verified and staged {count} native packages for the beta release.')
