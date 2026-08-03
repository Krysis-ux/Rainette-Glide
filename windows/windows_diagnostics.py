"""Windows-only diagnostics for Rainette Universal Mouse.

This script never moves or clicks the pointer. It validates the installation,
prints Windows-specific guidance, and briefly probes available cameras.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import platform
import struct
import sys

from universal_mouse_app import (
    open_camera,
    platform_profile,
    resource_path,
    windows_camera_guidance,
    windows_edition_details,
)


def check_import(module_name: str) -> tuple[bool, str]:
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", "installed")
        return True, str(version)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    print("RAINETTE UNIVERSAL MOUSE - WINDOWS DIAGNOSTICS")
    print("=" * 58)
    print(f"Operating system: {platform.platform()}")
    print(f"Windows edition: {windows_edition_details()}")
    print(f"Python: {sys.version.split()[0]} ({struct.calcsize('P') * 8}-bit)")
    print(f"Executable: {sys.executable}")
    print(f"Frozen build: {bool(getattr(sys, 'frozen', False))}")
    print()

    all_imports_ok = True
    for module_name in ("cv2", "mediapipe", "pyautogui", "PIL", "screeninfo"):
        ok, detail = check_import(module_name)
        all_imports_ok = all_imports_ok and ok
        print(f"{'PASS' if ok else 'FAIL'} import {module_name}: {detail}")

    model = resource_path("hand_landmarker.task")
    model_ok = model.is_file() and model.stat().st_size > 1_000_000
    print(
        f"{'PASS' if model_ok else 'FAIL'} MediaPipe model: "
        f"{model} ({model.stat().st_size if model.exists() else 0} bytes)"
    )
    print()

    if platform.system() != "Windows":
        print("FAIL: This diagnostic package is intended for Windows.")
        return 1
    if not all_imports_ok or not model_ok:
        print("Run setup_windows.bat again before testing the camera.")
        return 1

    import cv2

    print("Testing camera backends. The camera light may turn on briefly...")
    capture = None
    try:
        capture, index, backend = open_camera(
            cv2,
            platform_profile(),
            preferred_index=0,
            probe_attempts=25,
            probe_delay=0.04,
        )
        ok, frame = capture.read()
        if not ok or frame is None:
            raise RuntimeError("The selected camera stopped before the final diagnostic frame.")
        print(f"PASS camera: index {index}, backend {backend}, frame {frame.shape}")
        print("No mouse-control actions were performed.")
        return 0
    except Exception as exc:
        print(f"FAIL camera: {exc}")
        print(windows_camera_guidance())
        return 2
    finally:
        if capture is not None:
            capture.release()


if __name__ == "__main__":
    raise SystemExit(main())
