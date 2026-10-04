"""Compare packaged bytecode with the exact staged source; run in build venv."""
import hashlib
import json
import marshal
from pathlib import Path
import platform
import sys
import types
from PyInstaller.archive.readers import CArchiveReader

repo = Path(__file__).resolve().parents[3]
evidence = Path(__file__).resolve().parent
source = repo / 'dist/verification-20261004/source'
bundle = source.parent / 'VerseView Detector Test.app'
executable = bundle / 'Contents/MacOS/VerseView_Detector'
archive = CArchiveReader(str(executable))
pyz = archive.open_embedded_archive('PYZ.pyz')

def descriptor(obj):
    if isinstance(obj, types.CodeType):
        # Only co_filename is build-specific. Include instructions, constants,
        # argument/closure metadata, exception tables and line locations.
        attrs = ('co_argcount', 'co_posonlyargcount', 'co_kwonlyargcount',
                 'co_nlocals', 'co_stacksize', 'co_flags', 'co_code', 'co_consts',
                 'co_names', 'co_varnames', 'co_name', 'co_qualname',
                 'co_firstlineno', 'co_linetable', 'co_exceptiontable',
                 'co_freevars', 'co_cellvars')
        return {attr: descriptor(getattr(obj, attr)) for attr in attrs}
    if isinstance(obj, bytes):
        return {'bytes': obj.hex()}
    if isinstance(obj, (tuple, list)):
        return [descriptor(x) for x in obj]
    if isinstance(obj, frozenset):
        return {'frozenset': sorted([descriptor(x) for x in obj], key=repr)}
    if isinstance(obj, complex):
        return {'complex': repr(obj)}
    if obj is Ellipsis:
        return {'ellipsis': True}
    return obj

def digest(code):
    value = json.dumps(descriptor(code), sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(value.encode()).hexdigest()

checks = {}
for name in ('vv_gui', 'vv_streaming_master'):
    packed = marshal.loads(archive.extract(name)) if name in archive.toc else pyz.extract(name)
    expected = compile((source / (name + '.py')).read_bytes(), name + '.py',
                       'exec', dont_inherit=True, optimize=0)
    checks[name] = {'packaged_code_sha256': digest(packed),
                    'source_compilation_sha256': digest(expected),
                    'matches': descriptor(packed) == descriptor(expected)}
assert all(check['matches'] for check in checks.values()), checks
provenance_path = evidence / 'provenance.json'
provenance = json.loads(provenance_path.read_text())
provenance.update(artifact=str(bundle),
                  executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
                  python=sys.version, architecture=platform.machine(),
                  build_command='/tmp/verseview-package-build-20261004/bin/pyinstaller --clean -y verseview.spec',
                  working_directory=str(source), archive_verification=checks,
                  archive_verification_method='Recursive code object descriptors; co_filename omitted; canonical JSON SHA256')
provenance_path.write_text(json.dumps(provenance, indent=2) + '\n')
print(json.dumps(checks, indent=2))
