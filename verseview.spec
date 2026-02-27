# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# 1. Grab CustomTkinter data files (themes, json, etc.)
datas = collect_data_files('customtkinter')

# 2. Add your local project files if they aren't being picked up
# Format: ('source_path', 'destination_folder_in_app')
datas += [
    ('settings.py', '.'),
    ('bible_fetcher.py', '.'),
    ('parse_reference_eng.py', '.'),
    ('parse_reference_hindi.py', '.'),
    ('parse_reference_ml.py', '.'),
]

# 3. Path to your Tcl/Tk (Adjust if your version is 9.0 instead of 8.6)
# These paths are typical for Homebrew on Intel Macs
tcl_path = '/usr/local/opt/tcl-tk/lib/tcl8.6'
tk_path = '/usr/local/opt/tcl-tk/lib/tk8.6'

if os.path.exists(tcl_path):
    datas += [(tcl_path, 'tcl'), (tk_path, 'tk')]

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
        'certifi',
        'openai',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
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
    [],
    exclude_binaries=True,
    name='VerseView Detector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Set to True if you want a terminal window for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

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

if sys.platform == 'darwin':
    app = BUNDLE(
        coll, # Use 'coll' for Onedir mode
        name='VerseView Detector.app',
        icon=None,
        bundle_identifier='com.verseview.detector',
        info_plist={
            'NSMicrophoneUsageDescription': 'VerseView needs microphone access for live transcription.',
            'LSMinimumSystemVersion': '11.0',
            'CFBundleShortVersionString': '1.0.0',
            'LSEnvironment': {
                'TCL_LIBRARY': 'tcl',
                'TK_LIBRARY': 'tk',
            },
        },
    )