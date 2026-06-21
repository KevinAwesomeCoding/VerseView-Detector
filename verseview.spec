import sys
import os
import glob
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

block_cipher = None

# collect_data_files() returns proper 2-tuples (src, dest) that Analysis() expects.
# Tree() returns 3-tuple TOC objects which cause "too many values to unpack".
datas = collect_data_files('customtkinter')

datas += [
    ('settings.py', '.'),
    ('bible_fetcher.py', '.'),
    ('parse_reference_eng.py', '.'),
    ('parse_reference_hindi.py', '.'),
    ('parse_reference_ml.py', '.'),
    ('updater.py', '.'),
    ('version.txt', '.'),
    ('verseview_bot.py', '.'),
    ('vv_discord_bot.py', '.'),
    ('whisper_server_manager.py', '.'),
]

# Bundle the STT provider package source. PyInstaller already compiles these into
# the archive via the import graph, but shipping the source keeps the package
# present on disk (parity with the other hot-swappable modules above).
for _prov in glob.glob(os.path.join('stt_providers', '*.py')):
    datas.append((_prov, 'stt_providers'))

# ── Google Cloud Speech-to-Text (optional STT engine) ───────────────────────
# google-cloud-speech is a google.* namespace package built on gRPC + protobuf,
# with runtime version lookups via importlib.metadata. PyInstaller needs more
# than a bare hidden import to bundle it correctly:
#   • collect_submodules → pull the full google.cloud.speech / api_core / auth /
#                          protobuf / grpc / proto module trees (namespace
#                          packages are not followed reliably by the import graph)
#   • collect_data_files → grpc ships native libs + a bundled cacert.pem
#   • copy_metadata      → google-api-core and the speech client read their dist
#                          version via importlib.metadata at import time; a
#                          missing dist-info raises PackageNotFoundError at runtime
# Each step is wrapped defensively so a build environment WITHOUT the SDK still
# succeeds — GCP simply won't be bundled in that particular build.
_google_hiddenimports = []
for _gpkg in (
    'google.cloud.speech',
    'google.api_core',
    'google.auth',
    'google.oauth2',
    'google.protobuf',
    'grpc',
    'proto',
):
    try:
        _google_hiddenimports += collect_submodules(_gpkg)
    except Exception:
        pass

try:
    datas += collect_data_files('grpc')
except Exception:
    pass

for _gmeta in (
    'google-cloud-speech',
    'google-api-core',
    'google-auth',
    'grpcio',
    'protobuf',
    'proto-plus',
    'googleapis-common-protos',
):
    try:
        datas += copy_metadata(_gmeta)
    except Exception:
        pass

if sys.platform == 'win32':
    # Safety net for tkinter on Windows. PyInstaller's tkinter hook already
    # collects these for CPython 3.11, but this covers edge setups where the
    # DLLs / Tcl scripts live outside the default search path.
    import sysconfig
    _dlls = os.path.join(os.path.dirname(sys.executable), 'DLLs')
    for _pat, _dest in [
        (os.path.join(_dlls, 'tcl*.dll'),      '.'),
        (os.path.join(_dlls, 'tk*.dll'),       '.'),
        (os.path.join(_dlls, '_tkinter*.pyd'), '.'),
        (os.path.join(sys.exec_prefix, 'tcl', 'tcl8*', '*.tcl'), 'tcl'),
        (os.path.join(sys.exec_prefix, 'tcl', 'tk8*',  '*.tcl'), 'tk'),
    ]:
        for _f in glob.glob(_pat):
            datas.append((_f, _dest))

# NOTE (macOS): Tcl/Tk is bundled automatically by PyInstaller's tkinter hook for
# the python.org / actions-setup-python interpreter used in CI, and its runtime
# hook wires TCL_LIBRARY / TK_LIBRARY to the bundled copy. We deliberately do NOT
# copy Homebrew's Tcl/Tk: the old hardcoded /usr/local/opt/tcl-tk path does not
# exist on Apple Silicon (arm64 Homebrew lives under /opt/homebrew) and is absent
# on both CI runners regardless, so the manual copy was always a no-op. We also do
# NOT override TCL_LIBRARY / TK_LIBRARY via LSEnvironment any more — the previous
# override pointed at an empty Resources/tcl folder and broke Tcl initialisation,
# causing the app to crash on launch on Apple Silicon.

a = Analysis(
    ['vv_gui.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'customtkinter',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        '_tkinter',

        'pyaudio',

        # websockets — the Deepgram and Gladia providers stream over raw
        # websockets (no vendor SDK), so bundle every client backend so the
        # build works across websockets major versions (legacy vs asyncio).
        'websockets',
        'websockets.client',
        'websockets.legacy.client',
        'websockets.asyncio.client',

        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome.options',
        'selenium.webdriver.chrome.webdriver',
        'selenium.webdriver.chrome.service',

        'pynput.keyboard._darwin',
        'pynput.keyboard._win32',

        'webdriver_manager',

        # STT vendor SDKs that ARE imported directly.
        'sarvamai',
        'assemblyai',
        'assemblyai.streaming.v3',

        # STT provider package + every submodule. The factory selects providers
        # by class reference, so list them explicitly to guarantee bundling.
        'stt_providers',
        'stt_providers.base',
        'stt_providers.utils',
        'stt_providers.deepgram_provider',
        'stt_providers.assemblyai_provider',
        'stt_providers.sarvam_provider',
        'stt_providers.gladia_provider',
        'stt_providers.google_cloud_provider',
        'stt_providers.local_whisper_provider',
        'whisper_server_manager',

        'PyATEMMax',
        'zeroconf',
        'zeroconf._utils',
        'zeroconf._dns',
        'discord',
        'aiohttp',

        # Google Cloud STT — base hooks; the full submodule list (computed above
        # via collect_submodules) is appended to this list just below.
        'google.cloud.speech',
        'google.oauth2.service_account',
    ] + _google_hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='VerseView_Detector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX is OFF everywhere: it corrupts several Windows DLLs (vcruntime, _tkinter,
    # some extension modules) and, on macOS, mangles Mach-O binaries so they fail
    # code-signature validation — fatal on Apple Silicon, where unsigned/invalid
    # arm64 code is killed by the kernel ("crashes on launch"). UPX is also not
    # installed on the GitHub runners, so disabling it costs nothing.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    # Host architecture. Each runner builds its own native slice
    # (arm64 on macos-latest, x86_64 on macos-15-intel, x86_64 on windows-latest).
    # Do NOT pin to a single arch here — one spec serves all three runners.
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == 'darwin':
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name='VerseView Detector',
    )

    app = BUNDLE(
        coll,
        name='VerseView Detector.app',
        icon=None,
        bundle_identifier='com.verseview.detector',
        info_plist={
            # Required so macOS shows the mic-permission prompt (TCC). Without a
            # usage description the app is killed the moment it touches the mic.
            'NSMicrophoneUsageDescription':
                'VerseView needs microphone access to transcribe live audio.',
            # Real booleans (not the string 'False'): a <string>False</string>
            # value is non-empty and can be read as truthy, which would hide the
            # window / dock icon and look like a failed launch.
            'LSBackgroundOnly': False,
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.15',
        },
    )
