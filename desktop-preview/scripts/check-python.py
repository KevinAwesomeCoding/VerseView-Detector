"""Run the complete Python suite and expose CI failures in check annotations."""
import io
import os
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8', errors='backslashreplace')
suite = unittest.defaultTestLoader.discover(str(root / 'tests'))
output = io.StringIO()
result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
report = root / 'desktop-preview/test-results/python-checks.txt'
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(output.getvalue(), encoding='utf-8')
print(output.getvalue())
if os.getenv('GITHUB_ACTIONS') == 'true':
    def escape(value):
        return value.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    for test, trace in result.failures + result.errors:
        print('::error title=Python regression failure::' + escape(test.id() + '\n' + trace))
sys.exit(0 if result.wasSuccessful() else 1)
