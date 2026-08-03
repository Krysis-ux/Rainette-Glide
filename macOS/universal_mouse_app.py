"""Standalone Rainette Universal Mouse.

The application contains only the webcam hand-controlled pointer feature.  A
small controller window starts and stops a background tracking session, while a
separate preview window shows the live camera and MediaPipe hand landmarks.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import platform
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Sequence

from universal_mouse_core import (
    ClickLatch,
    GestureInterpreter,
    Point,
    ScreenBounds,
    ScrollTracker,
    map_camera_to_screen,
)


APP_NAME = "Rainette Universal Mouse"
CAMERA_WIDTH = 960
CAMERA_HEIGHT = 540
SMOOTHING = 0.42
SCROLL_INTERVAL_SECONDS = 1.0 / 20.0
PREVIEW_INTERVAL_MS = 30
LOGGER = logging.getLogger("rainette.universal_mouse")

# MediaPipe's standard 21-point hand skeleton.
HAND_CONNECTIONS: tuple[tuple[int, int], ...] = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),
)


@dataclass(frozen=True, slots=True)
class PlatformProfile:
    name: str
    camera_backend_names: tuple[str, ...]


def platform_profile() -> PlatformProfile:
    system = platform.system()
    if system == "Windows":
        return PlatformProfile("Windows", ("CAP_DSHOW", "CAP_MSMF", "CAP_ANY"))
    if system == "Darwin":
        return PlatformProfile("macOS", ("CAP_AVFOUNDATION", "CAP_ANY"))
    return PlatformProfile(system or "Unknown", ("CAP_ANY",))


def resource_path(filename: str) -> Path:
    """Resolve bundled files from source and PyInstaller builds."""
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return bundle_root / filename


def log_path() -> Path:
    system = platform.system()
    if system == "Darwin":
        folder = Path.home() / "Library" / "Logs" / "RainetteUniversalMouse"
    elif system == "Windows":
        folder = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "RainetteUniversalMouse"
    else:
        folder = Path.home() / ".rainette-universal-mouse"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "universal_mouse.log"


def configure_logging() -> None:
    try:
        logging.basicConfig(
            filename=log_path(),
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(threadName)s %(message)s",
        )
    except OSError:
        logging.basicConfig(level=logging.INFO)
    LOGGER.info("Application started on %s", platform.platform())


def determine_screen_bounds(pyautogui_module) -> ScreenBounds:
    """Return the union of all displays when screeninfo is available."""
    try:
        from screeninfo import get_monitors

        monitors = get_monitors()
        if monitors:
            left = min(m.x for m in monitors)
            top = min(m.y for m in monitors)
            right = max(m.x + m.width for m in monitors)
            bottom = max(m.y + m.height for m in monitors)
            return ScreenBounds(left, top, right - left, bottom - top)
    except Exception:
        LOGGER.exception("Could not read multi-monitor bounds; using primary display")

    width, height = pyautogui_module.size()
    return ScreenBounds(0, 0, int(width), int(height))


def ensure_macos_permissions(
    *,
    status_callback: Callable[[str], None] | None = None,
    accessibility_timeout_seconds: float = 120.0,
) -> None:
    """Request Camera and Accessibility access before opening the camera.

    The PyInstaller app also carries NSCameraUsageDescription in its Info.plist.
    This function converts denied or missing permission states into a readable
    in-app error instead of allowing camera initialization to fail opaquely.
    """
    if platform.system() != "Darwin":
        return

    try:
        import AVFoundation
    except ImportError as exc:
        raise RuntimeError(
            "macOS camera permission support is missing. Run setup_macos.command again."
        ) from exc

    status = AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_(
        AVFoundation.AVMediaTypeVideo
    )
    if status == AVFoundation.AVAuthorizationStatusNotDetermined:
        completed = threading.Event()
        granted_holder = {"granted": False}

        def permission_result(granted) -> None:
            granted_holder["granted"] = bool(granted)
            completed.set()

        AVFoundation.AVCaptureDevice.requestAccessForMediaType_completionHandler_(
            AVFoundation.AVMediaTypeVideo,
            permission_result,
        )
        if not completed.wait(timeout=60):
            raise RuntimeError(
                "Camera permission request timed out. Open System Settings > Privacy & Security > Camera."
            )
        if not granted_holder["granted"]:
            raise RuntimeError(
                "Camera access was not allowed. Enable Rainette Universal Mouse (or Python/Terminal) "
                "in System Settings > Privacy & Security > Camera, then turn it on again."
            )
    elif status != AVFoundation.AVAuthorizationStatusAuthorized:
        raise RuntimeError(
            "Camera access is blocked. Enable Rainette Universal Mouse (or Python/Terminal) "
            "in System Settings > Privacy & Security > Camera, then turn it on again."
        )

    # Accessibility APIs are part of the ApplicationServices/HIServices
    # framework.  Some PyObjC releases also re-export them from Quartz, but
    # that is not guaranteed.  Prefer the owning framework and retain the
    # Quartz fallback for older environments.
    try:
        import ApplicationServices as accessibility_api
    except ImportError:
        try:
            import Quartz as accessibility_api
        except ImportError as exc:
            raise RuntimeError(
                "macOS Accessibility permission support is missing. "
                "Run setup_macos.command again."
            ) from exc

    trust_check = getattr(
        accessibility_api, "AXIsProcessTrustedWithOptions", None
    )
    prompt_key = getattr(
        accessibility_api, "kAXTrustedCheckOptionPrompt", None
    )
    if not callable(trust_check) or prompt_key is None:
        raise RuntimeError(
            "The installed macOS Accessibility bindings are incomplete. "
            "Run setup_macos.command again to install "
            "pyobjc-framework-ApplicationServices."
        )

    trusted = bool(trust_check({prompt_key: True}))
    if not trusted:
        if status_callback is not None:
            status_callback(
                "Waiting for Accessibility permission… Enable Rainette Universal Mouse "
                "in System Settings > Privacy & Security > Accessibility."
            )
        deadline = time.monotonic() + max(1.0, float(accessibility_timeout_seconds))
        while time.monotonic() < deadline:
            time.sleep(1.0)
            if bool(trust_check({prompt_key: False})):
                trusted = True
                break

    if not trusted:
        raise RuntimeError(
            "Accessibility access was not enabled in time. Open System Settings > Privacy & "
            "Security > Accessibility and enable Rainette Universal Mouse. If you launched the "
            "source .command instead of the native app, macOS may list Terminal or Python."
        )


def _frame_is_visible(frame) -> bool:
    """Reject placeholder frames that are effectively all black.

    Some macOS camera backends report that a device opened successfully while
    returning zero-filled frames. A real dark room still has sensor variation,
    so both peak brightness and variation are checked conservatively.
    """
    if frame is None:
        return False
    try:
        if getattr(frame, "size", 0) <= 0:
            return False
        peak = float(frame.max())
        variation = float(frame.std())
        return peak > 8.0 and variation > 0.5
    except Exception:
        LOGGER.exception("Could not inspect camera probe frame")
        return False


def _camera_backend_options(cv2_module, profile: PlatformProfile) -> list[tuple[str, int | None]]:
    """Return deterministic backend order with native backends first."""
    explicit: list[tuple[str, int]] = []
    any_backend: tuple[str, int] | None = None
    seen_values: set[int] = set()
    for backend_name in profile.camera_backend_names:
        backend = getattr(cv2_module, backend_name, None)
        if backend is None or backend in seen_values:
            continue
        seen_values.add(backend)
        label = backend_name.removeprefix("CAP_").lower()
        if backend_name == "CAP_ANY":
            any_backend = (label, backend)
        else:
            explicit.append((label, backend))

    options: list[tuple[str, int | None]] = [*explicit, ("default", None)]
    if any_backend is not None and any_backend[1] != 0:
        options.append(any_backend)
    return options

def _probe_capture(capture, *, attempts: int, delay: float) -> bool:
    """Wait briefly for a camera to produce a non-placeholder frame."""
    attempts = max(1, int(attempts))
    for attempt in range(attempts):
        ok, frame = capture.read()
        if ok and _frame_is_visible(frame):
            LOGGER.info(
                "Camera probe succeeded on frame %s (max=%.1f std=%.2f)",
                attempt + 1,
                float(frame.max()),
                float(frame.std()),
            )
            return True
        if delay > 0:
            time.sleep(delay)
    return False

def open_camera(
    cv2_module,
    profile: PlatformProfile,
    preferred_index: int = 0,
    *,
    probe_attempts: int = 45,
    probe_delay: float = 0.04,
):
    """Open and validate a webcam using native backends and index fallbacks.

    ``isOpened()`` alone is not enough on macOS: AVFoundation/default camera
    handles can open while returning only black placeholder frames. Every
    candidate is warmed up and validated before it is selected.
    """
    indices = [preferred_index] + [index for index in range(5) if index != preferred_index]
    backend_options = _camera_backend_options(cv2_module, profile)

    attempts: list[str] = []
    blank_streams: list[str] = []
    for index in indices:
        for backend_name, backend in backend_options:
            attempt_name = f"camera {index}/{backend_name}"
            attempts.append(attempt_name)
            capture = None
            selected = False
            try:
                capture = (
                    cv2_module.VideoCapture(index)
                    if backend is None
                    else cv2_module.VideoCapture(index, backend)
                )
                if capture is None or not capture.isOpened():
                    continue

                capture.set(cv2_module.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                capture.set(cv2_module.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                try:
                    capture.set(cv2_module.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass

                LOGGER.info("Probing %s", attempt_name)
                if not _probe_capture(
                    capture, attempts=probe_attempts, delay=probe_delay
                ):
                    blank_streams.append(attempt_name)
                    LOGGER.warning("Rejected blank/unusable stream from %s", attempt_name)
                    continue

                LOGGER.info("Opened usable %s", attempt_name)
                selected = True
                return capture, index, backend_name
            except Exception:
                LOGGER.exception("Camera attempt failed: %s", attempt_name)
            finally:
                if capture is not None and not selected:
                    try:
                        capture.release()
                    except Exception:
                        pass

    guidance = ""
    if profile.name == "macOS":
        guidance = (
            " Check System Settings > Privacy & Security > Camera. Quit FaceTime, "
            "Zoom, Photo Booth, browser video calls, and Continuity Camera sessions."
        )
    elif profile.name == "Windows":
        guidance = " Check Settings > Privacy & security > Camera and allow desktop apps."

    if blank_streams:
        raise RuntimeError(
            "Camera devices opened but returned only blank frames. Tried "
            + ", ".join(attempts)
            + "."
            + guidance
        )
    raise RuntimeError(
        "Could not open a webcam. Tried " + ", ".join(attempts) + "." + guidance
    )

def draw_hand_overlay(
    cv2_module,
    frame,
    landmarks: Sequence[Point],
    gesture_mode: str,
):
    """Draw an animated-looking MediaPipe skeleton and gesture label."""
    if len(landmarks) < 21:
        return frame
    height, width = frame.shape[:2]
    pixels = [
        (
            max(0, min(width - 1, int(point.x * width))),
            max(0, min(height - 1, int(point.y * height))),
        )
        for point in landmarks[:21]
    ]

    line_color = (245, 245, 245)
    point_color = (40, 220, 170)
    active_color = (0, 210, 255) if gesture_mode == "pinch" else (255, 255, 255)

    for start, end in HAND_CONNECTIONS:
        cv2_module.line(
            frame,
            pixels[start],
            pixels[end],
            line_color,
            2,
            cv2_module.LINE_AA,
        )
    for index, center in enumerate(pixels):
        radius = 7 if index in {4, 8, 12} else 4
        color = active_color if index in {4, 8} else point_color
        cv2_module.circle(frame, center, radius, color, -1, cv2_module.LINE_AA)

    # A larger ring around the controlling fingertip makes motion easy to see.
    pulse_radius = 14 if int(time.monotonic() * 4) % 2 == 0 else 18
    cv2_module.circle(
        frame,
        pixels[8],
        pulse_radius,
        active_color,
        2,
        cv2_module.LINE_AA,
    )
    cv2_module.putText(
        frame,
        gesture_mode.upper().replace("NO-HAND", "NO HAND"),
        (24, 38),
        cv2_module.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
        cv2_module.LINE_AA,
    )
    return frame


def draw_no_hand_overlay(cv2_module, frame):
    cv2_module.putText(
        frame,
        "SHOW ONE HAND",
        (24, 38),
        cv2_module.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
        cv2_module.LINE_AA,
    )
    return frame


class UniversalMouseEngine:
    def __init__(
        self,
        *,
        status_callback: Callable[[str, str], None],
        stopped_callback: Callable[[], None],
        frame_callback: Callable[[object], None],
        camera_index: int = 0,
    ) -> None:
        self._status_callback = status_callback
        self._stopped_callback = stopped_callback
        self._frame_callback = frame_callback
        self._camera_index = camera_index
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="universal-mouse", daemon=True)
        self._thread.start()

    def stop(self, *, wait: bool = False) -> None:
        self._stop_event.set()
        if wait and self._thread is not None:
            self._thread.join(timeout=4.0)

    def _status(self, state: str, detail: str) -> None:
        self._status_callback(state, detail)

    def _run(self) -> None:
        capture = None
        landmarker = None
        click_latch = None
        try:
            self._status("STARTING", "Requesting permissions and opening camera…")
            ensure_macos_permissions(
                status_callback=lambda detail: self._status("STARTING", detail)
            )

            try:
                import cv2
                import mediapipe as mp
                from mediapipe.tasks import python as mp_python
                from mediapipe.tasks.python import vision as mp_vision
                import pyautogui
            except ImportError as exc:
                raise RuntimeError(
                    "A required package is missing. Run the included setup script first. "
                    f"({exc})"
                ) from exc

            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0
            fail_safe_error = getattr(pyautogui, "FailSafeException", Exception)
            bounds = determine_screen_bounds(pyautogui)
            profile = platform_profile()
            capture, camera_index, camera_backend = open_camera(
                cv2, profile, preferred_index=self._camera_index
            )

            model_path = resource_path("hand_landmarker.task")
            if not model_path.exists():
                raise RuntimeError(f"Missing MediaPipe hand model: {model_path}")

            options = mp_vision.HandLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
                running_mode=mp_vision.RunningMode.VIDEO,
                num_hands=1,
                min_hand_detection_confidence=0.5,
                min_hand_presence_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            landmarker = mp_vision.HandLandmarker.create_from_options(options)
            interpreter = GestureInterpreter(pinch_threshold=0.22)
            scroll_tracker = ScrollTracker(gain=180, deadzone=0.01)

            def emit_click(action: str) -> None:
                if action == "down":
                    pyautogui.mouseDown(button="left", _pause=False)
                else:
                    pyautogui.mouseUp(button="left", _pause=False)

            click_latch = ClickLatch(emit_click)
            cursor_x = bounds.left + bounds.width / 2
            cursor_y = bounds.top + bounds.height / 2
            last_timestamp_ms = 0
            last_scroll_time = 0.0
            last_mode = ""

            self._status(
                "ON",
                f"Camera {camera_index} · {camera_backend} · tracking in background",
            )

            consecutive_read_failures = 0
            while not self._stop_event.is_set():
                ok, frame = capture.read()
                if not ok:
                    consecutive_read_failures += 1
                    if consecutive_read_failures >= 30:
                        raise RuntimeError(
                            "The camera stopped returning frames. Close other camera apps and try again."
                        )
                    time.sleep(0.03)
                    continue
                consecutive_read_failures = 0

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                timestamp_ms = max(last_timestamp_ms + 1, int(time.monotonic() * 1000))
                last_timestamp_ms = timestamp_ms
                result = landmarker.detect_for_video(mp_image, timestamp_ms)

                if not result.hand_landmarks:
                    click_latch.release()
                    scroll_tracker.reset()
                    draw_no_hand_overlay(cv2, frame)
                    self._frame_callback(frame.copy())
                    if last_mode != "no-hand":
                        self._status("ON", "No hand detected")
                        last_mode = "no-hand"
                    continue

                landmarks = [
                    Point(float(point.x), float(point.y), float(point.z))
                    for point in result.hand_landmarks[0]
                ]
                gesture = interpreter.interpret(landmarks)
                draw_hand_overlay(cv2, frame, landmarks, gesture.mode)
                self._frame_callback(frame.copy())

                try:
                    if gesture.mode in {"pointer", "pinch"}:
                        scroll_tracker.reset()
                        target_x, target_y = map_camera_to_screen(
                            gesture.index_x, gesture.index_y, bounds
                        )
                        cursor_x += (target_x - cursor_x) * SMOOTHING
                        cursor_y += (target_y - cursor_y) * SMOOTHING
                        pyautogui.moveTo(int(cursor_x), int(cursor_y), duration=0, _pause=False)
                        click_latch.update(gesture.pinch)
                    elif gesture.mode == "scroll":
                        click_latch.release()
                        now = time.monotonic()
                        units = scroll_tracker.update(gesture.index_y)
                        if units and now - last_scroll_time >= SCROLL_INTERVAL_SECONDS:
                            pyautogui.scroll(units, _pause=False)
                            last_scroll_time = now
                    else:
                        click_latch.release()
                        scroll_tracker.reset()
                except fail_safe_error:
                    raise RuntimeError(
                        "Emergency stop triggered because the cursor reached the top-left corner."
                    )

                if gesture.mode != last_mode:
                    labels = {
                        "pointer": "Index finger · moving pointer",
                        "pinch": "Pinch held · clicking/dragging",
                        "scroll": "Two-finger vertical scroll",
                        "idle": "Show only the index finger",
                    }
                    self._status("ON", labels.get(gesture.mode, gesture.mode))
                    last_mode = gesture.mode

        except Exception as exc:
            LOGGER.exception("Universal Mouse session failed")
            self._status("ERROR", str(exc))
        finally:
            if click_latch is not None:
                try:
                    click_latch.release()
                except Exception:
                    LOGGER.exception("Could not release mouse button")
            if landmarker is not None:
                try:
                    landmarker.close()
                except Exception:
                    LOGGER.exception("Could not close hand landmarker")
            if capture is not None:
                try:
                    capture.release()
                except Exception:
                    LOGGER.exception("Could not release camera")
            self._status("OFF", "Camera released")
            self._stopped_callback()


class UniversalMouseWindow:
    BG = "#0b0b0c"
    PANEL = "#151517"
    TEXT = "#f7f7f7"
    MUTED = "#a0a0a6"
    ON = "#f4f4f5"
    OFF = "#303034"
    OFF_TEXT = "#000000"
    ERROR = "#ff6b6b"

    def __init__(self, expected_platform: str | None = None) -> None:
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("320x210")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        current_profile = platform_profile()
        if expected_platform and current_profile.name != expected_platform:
            messagebox.showwarning(
                APP_NAME,
                f"This package is intended for {expected_platform}, but it is running on {current_profile.name}.",
            )

        self._is_on = False
        self._last_error = ""
        self._preview_user_closed = False
        self._frame_queue: queue.Queue[object] = queue.Queue(maxsize=1)
        self.preview_window: tk.Toplevel | None = None
        self.preview_image_label: tk.Label | None = None
        self.preview_status_label: tk.Label | None = None
        self._preview_photo = None

        self.engine = UniversalMouseEngine(
            status_callback=self._thread_status,
            stopped_callback=self._thread_stopped,
            frame_callback=self._thread_frame,
        )

        frame = tk.Frame(self.root, bg=self.PANEL, padx=18, pady=16)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        self.title_label = tk.Label(
            frame,
            text="UNIVERSAL MOUSE",
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Arial", 10, "bold"),
        )
        self.title_label.pack(pady=(0, 10))

        self.toggle_button = tk.Button(
            frame,
            text="OFF",
            command=self.toggle,
            bg=self.OFF,
            fg=self.OFF_TEXT,
            activebackground=self.OFF,
            activeforeground=self.OFF_TEXT,
            relief="flat",
            bd=0,
            font=("Arial", 30, "bold"),
            cursor="hand2",
            height=1,
        )
        self.toggle_button.pack(fill="x", ipady=8)

        self.status_label = tk.Label(
            frame,
            text="Camera off",
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Arial", 10),
            wraplength=270,
            justify="center",
        )
        self.status_label.pack(pady=(12, 0))
        self.root.after(PREVIEW_INTERVAL_MS, self._poll_preview_frames)

    def _thread_status(self, state: str, detail: str) -> None:
        try:
            self.root.after(0, lambda: self._apply_status(state, detail))
        except tk.TclError:
            pass

    def _thread_stopped(self) -> None:
        try:
            self.root.after(0, self._mark_stopped)
        except tk.TclError:
            pass

    def _thread_frame(self, frame) -> None:
        if self._preview_user_closed:
            return
        try:
            self._frame_queue.put_nowait(frame)
        except queue.Full:
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._frame_queue.put_nowait(frame)
            except queue.Full:
                pass

    def _open_preview(self, detail: str = "Opening camera…") -> None:
        if self.preview_window is not None:
            if self.preview_status_label is not None:
                self.preview_status_label.configure(text=detail)
            return

        preview = tk.Toplevel(self.root)
        preview.title("Universal Mouse · Camera")
        preview.geometry("960x590")
        preview.minsize(640, 400)
        preview.configure(bg="#000000")
        preview.protocol("WM_DELETE_WINDOW", self._on_preview_close)
        self.preview_window = preview

        self.preview_image_label = tk.Label(
            preview,
            text="Requesting permissions and opening camera…",
            bg="#000000",
            fg="#ffffff",
            font=("Arial", 16, "bold"),
        )
        self.preview_image_label.pack(fill="both", expand=True)
        self.preview_status_label = tk.Label(
            preview,
            text=detail,
            bg="#111111",
            fg="#d9d9d9",
            font=("Arial", 10),
            pady=8,
        )
        self.preview_status_label.pack(fill="x")

    def _close_preview_window(self) -> None:
        preview = self.preview_window
        self.preview_window = None
        self.preview_image_label = None
        self.preview_status_label = None
        self._preview_photo = None
        if preview is not None:
            try:
                preview.destroy()
            except tk.TclError:
                pass

    def _on_preview_close(self) -> None:
        """Closing the webcam preview stops the current tracking session."""
        self._preview_user_closed = True
        self.engine.stop()
        preview = self.preview_window
        self.preview_window = None
        self.preview_image_label = None
        self.preview_status_label = None
        self._preview_photo = None
        if preview is not None:
            try:
                preview.destroy()
            except Exception:
                pass

    def _poll_preview_frames(self) -> None:
        latest = None
        while True:
            try:
                latest = self._frame_queue.get_nowait()
            except queue.Empty:
                break

        if latest is not None and not self._preview_user_closed:
            self._open_preview("Live · close this window to stop the session")
            try:
                from PIL import Image, ImageTk

                rgb = latest[:, :, ::-1].copy()
                image = Image.fromarray(rgb)
                image.thumbnail((960, 540), Image.Resampling.LANCZOS)
                self._preview_photo = ImageTk.PhotoImage(image=image)
                if self.preview_image_label is not None:
                    self.preview_image_label.configure(image=self._preview_photo, text="")
            except Exception as exc:
                LOGGER.exception("Could not display preview frame")
                self._apply_status("ERROR", f"Camera opened, but preview failed: {exc}")
                self.engine.stop()

        try:
            self.root.after(PREVIEW_INTERVAL_MS, self._poll_preview_frames)
        except tk.TclError:
            pass

    def _apply_status(self, state: str, detail: str) -> None:
        if state == "ERROR":
            self._last_error = detail
            self.status_label.configure(text=detail, fg=self.ERROR)
            self.toggle_button.configure(
                text="OFF",
                bg=self.OFF,
                fg=self.OFF_TEXT,
                activeforeground=self.OFF_TEXT,
                state="normal",
            )
            self._is_on = False
            if self.preview_status_label is not None:
                self.preview_status_label.configure(text=detail, fg=self.ERROR)
            return
        if state == "STARTING":
            self._preview_user_closed = False
            self._open_preview(detail)
            self.status_label.configure(text=detail, fg=self.MUTED)
            self.toggle_button.configure(
                text="…",
                bg=self.OFF,
                fg=self.OFF_TEXT,
                state="disabled",
            )
            return
        if state == "ON":
            self._is_on = True
            self.status_label.configure(text=detail, fg=self.MUTED)
            self.toggle_button.configure(
                text="ON",
                bg=self.ON,
                fg="#111111",
                activeforeground="#111111",
                state="normal",
            )
            if self.preview_status_label is not None:
                self.preview_status_label.configure(text=detail, fg="#d9d9d9")
            return
        if state == "OFF" and not self._last_error:
            self.status_label.configure(text=detail, fg=self.MUTED)

    def _mark_stopped(self) -> None:
        self._is_on = False
        self.toggle_button.configure(
            text="OFF",
            bg=self.OFF,
            fg=self.OFF_TEXT,
            activeforeground=self.OFF_TEXT,
            state="normal",
        )
        self._close_preview_window()
        if not self._last_error:
            self.status_label.configure(text="Camera off", fg=self.MUTED)

    def toggle(self) -> None:
        if self.engine.running or self._is_on:
            self._last_error = ""
            self._preview_user_closed = True
            self.status_label.configure(text="Stopping…", fg=self.MUTED)
            self.toggle_button.configure(text="…", state="disabled")
            self._close_preview_window()
            self.engine.stop()
        else:
            self._last_error = ""
            self._preview_user_closed = False
            self.engine.start()

    def close(self) -> None:
        self._preview_user_closed = True
        self.engine.stop(wait=True)
        self._close_preview_window()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self) -> None:
        self.root.mainloop()


def main(expected_platform: str | None = None) -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    configure_logging()
    try:
        UniversalMouseWindow(expected_platform=expected_platform).run()
    except Exception as exc:
        LOGGER.exception("Fatal application error")
        try:
            messagebox.showerror(APP_NAME, f"Universal Mouse could not start:\n\n{exc}\n\nLog: {log_path()}")
        except Exception:
            raise


if __name__ == "__main__":
    main()
