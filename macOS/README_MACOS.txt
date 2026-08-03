RAINETTE UNIVERSAL MOUSE — macOS v4

This package contains only the isolated webcam hand-controlled mouse feature.
It does not include Rainette/Jarvis, AI, browser automation, music, or other tools.

RECOMMENDED FIRST RUN — NATIVE APP
1. Extract this ZIP into a new folder. Do not overwrite v2 or v3.
2. Double-click run_macos.command.
3. The first run creates and installs this native app:
      ~/Applications/RainetteUniversalMouse.app
4. The app opens automatically. Press the large OFF button to turn it ON.
5. Allow Camera access when macOS asks.
6. Enable RainetteUniversalMouse in:
      System Settings > Privacy & Security > Accessibility
   The app waits for this permission instead of immediately closing.

WHY THE NATIVE APP IS IMPORTANT
Running Python directly from a .command file makes macOS attribute pointer
control to Terminal or Python. v4 builds, ad-hoc signs, installs, and launches a
real .app so Camera and Accessibility permissions belong to
RainetteUniversalMouse instead of Terminal.

CAMERA FIX IN v4
Some OpenCV camera handles report "opened" while returning only zero-filled
black frames. v4 now:
- tries the native AVFoundation backend before OpenCV's default backend;
- warms up and validates each camera stream;
- rejects blank placeholder streams;
- automatically tries camera indexes 0 through 4;
- gives a specific error if every available stream is blank.

WHAT OPENS
- A small ON/OFF controller.
- A separate live webcam window.
- The webcam window draws all 21 MediaPipe landmarks, hand connections,
  fingertip indicators, and the current gesture over the camera image.

GESTURES
- Index finger only: move the pointer.
- Thumb + index pinch: click. Keep pinched to drag.
- Index + middle fingers: move vertically to scroll.

BACKGROUND USE
- The controller and camera preview do not need to remain in front.
- Minimizing either window does not stop mouse control.
- Closing the camera preview ends the current tracking session and returns the
  controller to OFF.
- Closing the controller exits the entire app and releases the camera and any
  held mouse button.

FILES
- run_macos.command: opens the installed native app; builds it on first use.
- install_macos_app.command: manually rebuilds, signs, installs, and opens it.
- build_macos_app.command: creates a signed app inside ./dist without installing.
- setup_macos.command: installs the Python dependencies only.
- hand_landmarker.task: included MediaPipe hand-tracking model.

TROUBLESHOOTING
- Quit FaceTime, Zoom, Photo Booth, browser video calls, and Continuity Camera.
- In Camera and Accessibility settings, remove old v2/v3 entries if necessary.
- Keep only the newly installed RainetteUniversalMouse entry enabled.
- To force macOS to ask again, remove the old app entry, quit System Settings,
  reopen the app, and press ON.
- Log file:
  ~/Library/Logs/RainetteUniversalMouse/universal_mouse.log

If a .command file is blocked, Control-click it and choose Open.
