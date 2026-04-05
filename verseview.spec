import sys
import os
import glob
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# Collect customtkinter assets explicitly — collect_data_files alone misplaces
# the theme JSON files on Windows, causing blue.json not found at runtime.
import customtkinter as _ctk
_ctk_dir = os.path.dirname(_ctk.__file__)
datas = [(os.path.join(_ctk_dir, 'assets'), 'customtkinter/assets')]
# Also collect the rest of customtkinter data (fonts, images etc.)
datas += collect_data_files('customtkinter')
# Remove duplicates while preserving order
_seen = set()
_dedup = []
for item in datas:
    if item not in _seen:
        _seen.add(item)
        _dedup.append(item)
datas = _dedup

datas += collect_data_files('tkinter')
datas += [
    ('settings.py', '.'),
    ('bible_fetcher.py', '.'),
    ('parse_reference_eng.py', '.'),
    ('parse_reference_hindi.py', '.'),
    ('parse_reference_ml.py', '.'),
    ('updater.py', '.'),
    ('version.txt', '.'),
]


if sys.platform == 'win32':
    # Explicitly bundle tkinter DLLs — PyInstaller misses them on some Windows setups
    import glob, sysconfig
    _stdlib = sysconfig.get_path('stdlib')
    _dlls   = os.path.join(os.path.dirname(sys.executable), 'DLLs')
    for _pat, _dest in [
        (os.path.join(_dlls, 'tcl*.dll'),     '.'),
        (os.path.join(_dlls, 'tk*.dll'),      '.'),
        (os.path.join(_dlls, '_tkinter*.pyd'), '.'),
        (os.path.join(sys.exec_prefix, 'tcl', 'tcl8*', '*.tcl'), 'tcl'),
        (os.path.join(sys.exec_prefix, 'tcl', 'tk8*',  '*.tcl'), 'tk'),
    ]:
        for _f in glob.glob(_pat):
            datas.append((_f, _dest))

if sys.platform == 'darwin':
    tcl_lib = '/usr/local/opt/tcl-tk/lib/tcl8.6'
    tk_lib = '/usr/local/opt/tcl-tk/lib/tk8.6'
    if os.path.exists(tcl_lib):
        datas += [(tcl_lib, 'tcl'), (tk_lib, 'tk')]

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
        'websockets.legacy.client', 
        'selenium',
	    'selenium.webdriver',
	    'selenium.webdriver.chrome.options', 
	    'selenium.webdriver.chrome.webdriver',
	    'selenium.webdriver.chrome.service',
        'pynput.keyboard._darwin',
        'pynput.keyboard._win32',
        'webdriver_manager',
        'sarvamai',
        'keyboard',
        'PyATEMMax',
        'zeroconf',
        'zeroconf._utils',
        'zeroconf._dns',
    ],
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
