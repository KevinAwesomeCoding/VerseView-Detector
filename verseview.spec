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
        'deepgram',
        'sarvamai',
        'websockets',
        'websockets.legacy',
        'websockets.legacy.client',
        'selenium',
        'webdriver_manager',
        'webdriver_manager.chrome',
        'certifi',
        'openai',
        'requests',
        'vv_streaming_master',
        'parse_reference_eng',
        'parse_reference_hindi',
        'parse_reference_ml',
        'wave',
        'base64',
        'io',
        'unicodedata',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    no
