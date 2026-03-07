# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_all

datas_dg,  bins_dg,  hidden_dg  = collect_all('deepgram')
datas_sv,  bins_sv,  hidden_sv  = collect_all('sarvamai')
datas_cn,  bins_cn,  hidden_cn  = collect_all('charset_normalizer')

datas = collect_data_files('customtkinter')
datas += datas_dg + datas_sv + datas_cn
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

# pyobjc (needed by pynput on macOS) — only collect on macOS builds
extra_hidden = []
extra_bins   = []
extra_datas  = []
if sys.platform == 'darwin':
    try:
        d, b, h = collect_all('objc');        extra_datas+=d; extra_bins+=b; extra_hidden+=h
        d, b, h = collect_all('Foundation');  extra_datas+=d; extra_bins+=b; extra_hidden+=h
        d, b, h = collect_all('AppKit');      extra_datas+=d; extra_bins+=b; extra_hidden+=h
        d, b, h = collect_all('Quartz');      extra_datas+=d; extra_bins+=b; extra_hidden+=h
    except Exception:
        pass  # pyobjc not installed — pynput lazy import will handle gracefully
    datas += extra_datas

# UPX crashes on macOS ARM64 (Apple Silicon) — keep it only for Windows
USE_UPX = sys.platform == 'win32'

a = Analysis(
    ['vv_gui.py'],
    pathex=[],
    binaries=bins_dg + bins_sv + bins_cn + extra_bins,
    datas=datas,
    hiddenimports=[
        'customtkinter',
        'pyaudio',
        'requests',
        'charset_normalizer',
        'charset_normalizer.md__mypyc',
        'certifi',
        'websockets',
        'websockets.legacy.client',
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome.options',
        'selenium.webdriver.chrome.webdriver',
        'selenium.webdriver.chrome.service',
        'webdriver_manager',
        'openai',
        'deepgram',
        'sarvamai',
        'pynput',
        'pynput.keyboard',
        'pynput.keyboard._darwin',
        'pynput.keyboard._win32',
        'pynput.mouse._darwin',
        'pynput.mouse._win32',
        'keyboard',
        'objc',
        'Foundation',
        'AppKit',
        'Quartz',
    ] + hidden_dg + hidden_sv + hidden_cn + extra_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure)

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
    upx=USE_UPX,
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
            'NSMicrophoneUsageDescription': 'Needs mic for transcription',
            'LSEnvironment': {
                'TCL_LIBRARY': '@executable_path/../Resources/tcl',
                'TK_LIBRARY': '@executable_path/../Resources/tk',
            },
            'LSBackgroundOnly': 'False',
        },
    )
