# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

mediapipe_datas, mediapipe_binaries, mediapipe_hiddenimports = collect_all("mediapipe")

a = Analysis(
    ["universal_mouse_macos.py"],
    pathex=[],
    binaries=mediapipe_binaries,
    datas=mediapipe_datas + [("hand_landmarker.task", ".")],
    hiddenimports=mediapipe_hiddenimports + ["ApplicationServices", "HIServices"],
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
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="RainetteUniversalMouse",
)
app = BUNDLE(
    coll,
    name="RainetteUniversalMouse.app",
    bundle_identifier="com.rainette.universalmouse",
    info_plist={
        "NSCameraUsageDescription": (
            "Rainette Universal Mouse uses the camera only to track your hand "
            "and control the mouse pointer."
        ),
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.utilities",
        "CFBundleDisplayName": "Rainette Universal Mouse",
        "CFBundleName": "Rainette Universal Mouse",
        "CFBundleShortVersionString": "4.0",
        "CFBundleVersion": "4",
        "LSMinimumSystemVersion": "11.0",
    },
)
