# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from pathlib import Path

root = Path(SPECPATH).parent

hiddenimports = ['PySide6.QtSvg', 'qrcode.image.pil', 'qrcode.image.svg']
hiddenimports += collect_submodules('pygments.lexers')


a = Analysis(
    [str(root / 'src/clipo/__main__.py')],
    pathex=[str(root / 'src')],
    binaries=[],
    datas=[(str(root / 'src/clipo/resources'), 'clipo/resources'), (str(root / 'integrations/gnome'), 'clipo/resources/gnome')],
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
    [],
    exclude_binaries=True,
    name='clipo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='clipo',
)
