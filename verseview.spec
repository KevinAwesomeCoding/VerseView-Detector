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

# 2. Platform Specific Paths
if sys.platform == 'darwin':
    # Mac Tcl/Tk logic
    tcl_lib = '/usr/local/opt/tcl-tk/lib/tcl8.6'
    tk_lib = '/usr/local/opt/tcl-tk/lib/tk8.6'
    if os.path.exists(tcl_lib):
        datas += [(tcl_lib, 'tcl'), (tk_lib, 'tk')]
elif sys.platform == 'win32':
    # Windows usually bundles Tcl/Tk automatically, 
    # but we ensure the hidden imports cover it.
    pass

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
        'sarvamai' # Ensure Sarvam is included if using it
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

# Changed to ONEFILE for easier distribution on Windows
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,  # Included for OneFile
    a.zipfiles,  # Included for OneFile
    a.datas,     # Included for OneFile
    name='VerseView_Detector', # No spaces makes CLI life easier
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

# Mac Specific Bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
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