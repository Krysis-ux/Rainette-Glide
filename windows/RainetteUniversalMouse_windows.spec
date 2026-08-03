# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

mediapipe_datas, mediapipe_binaries, mediapipe_hiddenimports = collect_all("mediapipe")

a = Analysis(
    ["universal_mouse_windows.py"],
    pathex=[],
    binaries=mediapipe_binaries,
    datas=mediapipe_datas + [("hand_landmarker.task", ".")],
    hiddenimports=mediapipe_hiddenimports,
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
    name="RainetteUniversalMouse",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    uac_admin=False,
    uac_uiaccess=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="RainetteUniversalMouse",
)
