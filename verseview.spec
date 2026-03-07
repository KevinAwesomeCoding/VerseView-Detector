verseview
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_all

block_cipher = None

datas = collect_data_files('customtkinter')
datas += [
    ('settings.py', '.'),
    ('bible_fetcher.py', '.'),
    ('parse_reference_eng.py', '.'),
    ('parse_reference_hindi.py', '.'),
    ('parse_reference_ml.py', '.'),
]

if sys.platform == 'darwin':
    tcl_lib = '/usr/local/opt/tcl-tk/lib/tcl8.6'
    tk_lib  = '/usr/local/opt/tcl-tk/lib/tk8.6'
    if os.path.exists(tcl_lib):
        datas += [(tcl_lib, 'tcl'), (tk_lib, 'tk')]

# Pull in all of deepgram and sarvamai so nothing is missing at runtime
tmp_ret = collect_all('deepgram')
datas    += tmp_ret[0]; binaries  = tmp_ret[1]; hiddenimports_dg = tmp_ret[2]

tmp_ret2 = collect_all('sarvamai')
datas    += tmp_ret2[0]; binaries += tmp_ret2[1]; hiddenimports_sv = tmp_ret2[2]

a = Analysis(
    ['vv_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        # UI
        'customtkinter',
        # Audio
        'pyaudio',
        # Networking / requests
        'requests',
        'charset_normalizer',
        'charset_normalizer.md__mypyc',
        'certifi',
        'websockets',
        'websockets.legacy.client',
        # Selenium
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome.options',
        'selenium.webdriver.chrome.webdriver',
        'selenium.webdriver.chrome.service',
        'webdriver_manager',
        # STT / LLM
        'openai',
        'deepgram',
        'sarvamai',
        # Input / keyboard
        'pynput',
        'pynput.keyboard',
        'pynput.keyboard._darwin',
        'pynput.keyboard._win32',
        'pynput.mouse._darwin',
        'pynput.mouse._win32',
        'keyboard',
    ] + hiddenimports_dg + hiddenimports_sv,
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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
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
        upx=True,
        upx_exclude=[],
        name='VerseView Detector',
    )

    app = BUNDLE(
        coll,
        name='VerseView Detector.app',
        icon=None,
        bundle_identifier='com.verseview.detector',
        info_plist={
            'NSMicrophoneUsageDescription': 'Needs mic for transcription',
            'LSEnvironment': {
                'TCL_LIBRARY': '@executable_path/../Resources/tcl',
                'TK_LIBRARY': '@executable_path/../Resources/tk',
            },
            'LSBackgroundOnly': 'False',
        },
    )
