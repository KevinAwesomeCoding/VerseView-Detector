# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# 1. Collect CustomTkinter and local logic files
datas = collect_data_files('customtkinter')
datas += [
    ('settings.py', '.'),
    ('bible_fetcher.py', '.'),
    ('parse_reference_eng.py', '.'),
    ('parse_reference_hindi.py', '.'),
    ('parse_reference_ml.py', '.'),
]

# 2. Platform Specific Paths (Mac Tcl/Tk logic)
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
        'pyaudio', 
        'websockets.legacy.client', 
        'selenium', 
        'webdriver_manager',
        'sarvamai'
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

# 3. Create the Executable
# Notice: name='VerseView_Detector' (with underscore)
# By passing a.binaries and a.datas here, Windows builds as a SINGLE .exe file.
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

# 4. Create the Mac App Bundle (Mac Only)
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