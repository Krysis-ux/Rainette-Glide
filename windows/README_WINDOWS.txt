RAINETTE UNIVERSAL MOUSE — Windows v5

This package contains only the isolated webcam hand-controlled mouse feature.
It does not include Rainette/Jarvis, AI, browser automation, music, or other tools.

FIRST RUN
1. Extract the ZIP into a normal folder. Do not run it from inside the ZIP.
2. Double-click setup_windows.bat once.
3. Double-click run_windows.bat.
4. Press the large OFF button to turn tracking ON.

WINDOWS PERMISSIONS
Rainette Universal Mouse is an unpackaged desktop program. Windows normally does
not show a per-app Accessibility permission prompt like macOS.

Camera access is controlled here:
Settings > Privacy & security > Camera
- Camera access: ON
- Let desktop apps access your camera: ON

If camera startup fails, the app offers to open that Settings page automatically.
The app never requests microphone, location, files, contacts, or network access.

MOUSE CONTROL
Normal desktop windows require no special permission. Windows can block a normal
app from controlling an administrator/elevated window. Only run Universal Mouse
as administrator when you specifically need to control another elevated app.
Running as administrator is not needed for ordinary use and is not requested by
the included EXE manifest.

WHAT OPENS
- A small ON/OFF controller.
- A separate live webcam window.
- MediaPipe landmarks, hand connections, fingertip animation, and gesture status.

GESTURES
- Index finger only: move the pointer.
- Thumb + index pinch: click. Keep pinched to drag.
- Index + middle fingers: move vertically to scroll.

BACKGROUND USE
- Minimize either window and mouse control continues.
- Closing the webcam window ends the current tracking session.
- Closing the controller exits the app and releases the camera/mouse button.

WINDOWS-SPECIFIC RELIABILITY
- Per-monitor-v2 DPI awareness keeps cursor coordinates aligned on scaled and
  mixed-DPI monitors.
- DirectShow, Media Foundation, default backends, and camera indexes 0-4 are
  validated using real frames.
- Blank camera streams are rejected.
- Windows N/KN editions receive Media Feature Pack guidance.
- The EXE build does not request administrator access and does not use UPX.

DIAGNOSTICS
Double-click diagnose_windows.bat. It checks dependencies, model files, Windows
edition, and camera backends without moving or clicking the mouse.
For a visible console while running the full app, use run_windows_debug.bat.

CAMERA TROUBLESHOOTING
- Close Camera, Teams, Zoom, Discord, OBS, and browser video calls.
- Open a physical privacy shutter or enable the camera keyboard/Fn key.
- Check Device Manager > Cameras and update/re-enable the camera driver.
- Check antivirus or endpoint-security webcam blocking.
- On Windows N/KN, install Media Feature Pack from Optional features and restart.

LOG
%LOCALAPPDATA%\RainetteUniversalMouse\universal_mouse.log

OPTIONAL NATIVE EXE
1. Run build_windows_exe.bat on Windows.
2. Open dist\RainetteUniversalMouse\RainetteUniversalMouse.exe.

An unsigned locally built EXE may show Microsoft Defender SmartScreen. Building
locally reduces download reputation warnings, but a commercial code-signing
certificate would be required to remove them reliably for distributed builds.
