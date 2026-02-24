# -*- mode: python ; coding: utf-8 -*-
import sys

block_cipher = None

a = Analysis(
    ['vv_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'customtkinter',
        'pyaudio',
        'websockets',
        'websockets.legacy',
        'websockets.legacy.client',
        'sarvamai',
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.options',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.chrome.webdriver',
        'selenium.webdriver.common.by',
        'selenium.webdriver.common.keys',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.expected_conditions',
        'selenium.webdriver.remote.webdriver',
        'selenium.webdriver.remote.webelement',
        'webdriver_manager',
        'webdriver_manager.chrome',
        'certifi',
        'openai',
        'requests',
        'vv_streaming_master',
        'parse_reference_eng',
        'parse_reference_hindi',
        'parse_reference_ml',
        'bible_fetcher',
        'wave',
        'base64',
        'io',
        'unicodedata',
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
    [],
    name='VerseView Detector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=None,
    target_arch='universal2',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='VerseView Detector.app',
        icon=None,
        bundle_identifier='com.verseview.app',
        info_plist={
            'NSMicrophoneUsageDescription': 'VerseView needs microphone access for live transcription.',
            'LSMinimumSystemVersion': '11.0',
        },
    )
