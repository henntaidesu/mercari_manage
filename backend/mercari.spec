# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 规格：在 backend 目录执行
  pyinstaller mercari.spec --clean --noconfirm
首次打包若缺依赖，可在 hiddenimports 或 collect_all 中补充。
"""
import os

from PyInstaller.utils.hooks import collect_all

block_cipher = None
spec_dir = os.path.dirname(os.path.abspath(SPEC))

datas: list = []
binaries: list = []
hiddenimports: list = []

for pkg in (
    "uvicorn",
    "fastapi",
    "starlette",
    "pydantic",
    "anyio",
    "multipart",
    "dns",
    "jwt",
):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

for pkg in ("mitmproxy", "playwright", "easyocr", "PIL", "cryptography"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

a = Analysis(
    ["main.py"],
    pathex=[spec_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="mercari-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
