"""Build the native companion through the repository's existing PyInstaller spec."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
platform_name = sys.platform
arch = {'aarch64': 'arm64', 'arm64': 'arm64', 'x86_64': 'x64', 'AMD64': 'x64'}.get(platform.machine())
if platform_name not in ('darwin', 'win32') or not arch:
    raise SystemExit('Build the companion on a supported native Mac or Windows host.')
stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
output = root / 'desktop-preview' / 'backend-build' / f'{stamp}-{platform_name}-{arch}'
env = {**os.environ, 'VERSEVIEW_BUILD_HEADLESS': '1'}
subprocess.run([sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', '--distpath', str(output),
                '--workpath', str(output / 'work'), str(root / 'verseview.spec')], cwd=root, env=env, check=True)
backend = output / 'backend'
files = {}
for file in sorted(backend.rglob('*')):
    if file.is_symlink(): files[str(file.relative_to(backend)).replace('\\', '/')] = {'symlink': os.readlink(file)}
    elif file.is_file():
        with file.open('rb') as handle: digest = hashlib.file_digest(handle, 'sha256').hexdigest()
        files[str(file.relative_to(backend)).replace('\\', '/')] = {'sha256': digest}
sources = {}
for name in ['desktop_backend.py', 'backend_verification.py', 'desktop_control.py', 'desktop_settings.py',
             'observer_feed.py', 'settings.py', 'service_schedule.py', 'desktop_recovery.py', 'desktop_warmup.py', 'desktop_suggestions.py', 'desktop_outline.py', 'desktop_bot.py', 'desktop_bot_bridge.py', 'desktop_bot_process.py', 'desktop_sync.py', 'desktop_cloud_settings.py', 'vv_discord_bot.py', 'vv_streaming_master.py', 'free_cloud.py', 'contextual_watcher.py', 'verseview.spec', 'requirements.txt']:
    sources[name] = hashlib.sha256((root/name).read_bytes()).hexdigest()
manifest = {'schema': 1, 'platform': platform_name, 'arch': arch, 'builtAt': stamp,
            'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
            'sourceFiles': sources, 'files': files,
            'buildCommand': 'python desktop-preview/scripts/build-backend.py',
            'dependencies': subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True).splitlines()}
(backend / 'backend-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
(root/'desktop-preview/backend-build/latest.txt').write_text(str(backend)+'\n')
print(json.dumps({'backend': str(backend), 'platform': platform_name, 'arch': arch}))
