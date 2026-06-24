# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [
    ('src', 'src'),
    ('icon.ico', '.'),
    (r'C:\Users\PRO\AppData\Local\Programs\Python\Python39\lib\site-packages\tkinterdnd2\tkdnd', 'tkinterdnd2/tkdnd'),
    (r'C:\Users\PRO\AppData\Local\Programs\Python\Python39\lib\site-packages\customtkinter', 'customtkinter'),
]
binaries = []
hiddenimports = [
    'customtkinter',
    'tkinterdnd2',
    'fitz',
    'pymupdf',
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
]
tmp_ret = collect_all('fitz')
datas    += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

tmp_ret = collect_all('pymupdf')
datas    += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(
    ['app_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'numpy', 'pandas',
        'PIL', 'Pillow',
        'IPython', 'jupyter',
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx',
        'lxml', 'html5lib', 'bs4',
        'multiprocessing',
        '_tkinter.test',
        'unittest',
        'xmlrpc',
        'distutils',
        'setuptools',
        'pkg_resources',
    ],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # onedir: binários ficam na pasta
    name='Analisador de Faturas',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,               # UPX adiciona tempo de descompressão sem ganho real
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Analisador de Faturas',
)
