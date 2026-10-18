"""Retain native build diagnostics and expose failed-command details to checks."""
import os
from pathlib import Path
import re
import subprocess
import sys

label, *command = sys.argv[1:]
if not re.fullmatch(r'[a-z0-9-]+', label) or not command:
    raise SystemExit('Pass a diagnostic label and command')
root = Path(__file__).resolve().parents[1]
report = root / 'test-results' / ('ci-' + label + '.log')
report.parent.mkdir(parents=True, exist_ok=True)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
with report.open('w', encoding='utf-8') as log:
    child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding='utf-8', errors='replace')
    for line in child.stdout:
        log.write(line)
        print(line, end='', flush=True)
    code = child.wait()
if code and os.getenv('GITHUB_ACTIONS') == 'true':
    details = report.read_text(encoding='utf-8')[-45000:]
    details = details.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::error title=Native preview check failed::' + label + '%0A' + details)
sys.exit(code)
