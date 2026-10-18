"""Native CI startup smoke: frozen host, no GUI/audio/network/start command."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--backend', type=Path)
args = parser.parse_args()
backend = args.backend or Path((root/'backend-build/latest.txt').read_text().strip())
executable = backend / ('VerseViewBackend.exe' if os.name == 'nt' else 'VerseViewBackend')
with tempfile.TemporaryDirectory(prefix='vv-native-smoke-') as directory:
    profile = Path(directory)/'QA'/'Backend'
    result = subprocess.run([str(executable), '--profile', str(profile), '--verify-isolated'],
                            input='{"action":"shutdown"}\n', text=True, capture_output=True, timeout=25,
                            env={**os.environ, 'VV_PREVIEW_TEST_PROFILE': '1'})
    assert result.returncode == 0, 'Frozen backend did not exit cleanly'
    values=[]
    for line in result.stdout.splitlines():
        try: values.append(json.loads(line))
        except ValueError: pass
    ready = next(item for item in values if item.get('ready'))
    assert ready['frozen'] and not ready['guiImported'] and ready['verification']
    print(json.dumps({'result':'PASS','ready':ready,'platform':os.name,'audioOrPresentationStarted':False}))
