# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('src', 'src'), ('C:\\Users\\PRO\\AppData\\Local\\Programs\\Python\\Python39\\lib\\site-packages\\tkinterdnd2\\tkdnd', 'tkinterdnd2/tkdnd'), ('C:\\Users\\PRO\\AppData\\Local\\Programs\\Python\\Python39\\lib\\site-packages\\customtkinter', 'customtkinter')]
binaries = []
hiddenimports = ['customtkinter', 'tkinterdnd2', 'pdfminer', 'pdfminer.high_level', 'pdfminer.layout', 'pdfminer.pdfpage', 'pdfminer.pdfinterp', 'pdfminer.converter', 'openpyxl', 'openpyxl.styles', 'openpyxl.utils']
tmp_ret = collect_all('pdfplumber')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['app_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Analisador Claro Empresas',
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
