"""Pure gesture and coordinate logic for Rainette Universal Mouse.

This module intentionally has no camera, GUI, MediaPipe, or OS dependencies so
its behavior can be tested on any machine.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True, slots=True)
class ScreenBounds:
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class GestureResult:
    mode: str
    pinch: bool
    index_x: float
    index_y: float


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def map_camera_to_screen(
    x: float,
    y: float,
    bounds: ScreenBounds,
    *,
    x_min: float = 0.08,
    x_max: float = 0.92,
    y_min: float = 0.10,
    y_max: float = 0.90,
) -> tuple[int, int]:
    """Map a normalized camera point into the full virtual desktop.

    The inner camera rectangle maps to the complete screen, so the user does
    not need to reach the extreme edges of the webcam frame.
    """
    if bounds.width <= 0 or bounds.height <= 0:
        raise ValueError("screen bounds must have positive width and height")
    if not (x_min < x_max and y_min < y_max):
        raise ValueError("camera mapping minimums must be below maximums")

    normalized_x = (_clamp(x, x_min, x_max) - x_min) / (x_max - x_min)
    normalized_y = (_clamp(y, y_min, y_max) - y_min) / (y_max - y_min)
    max_x = bounds.left + bounds.width - 1
    max_y = bounds.top + bounds.height - 1
    screen_x = round(bounds.left + normalized_x * (bounds.width - 1))
    screen_y = round(bounds.top + normalized_y * (bounds.height - 1))
    return (
        int(_clamp(screen_x, bounds.left, max_x)),
        int(_clamp(screen_y, bounds.top, max_y)),
    )


def landmark_distance(a: Point, b: Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def pinch_ratio(landmarks: Sequence[Point]) -> float:
    """Return thumb/index distance normalized by wrist-to-palm distance."""
    if len(landmarks) < 21:
        raise ValueError("a MediaPipe hand must contain 21 landmarks")
    palm_scale = landmark_distance(landmarks[0], landmarks[9])
    if palm_scale < 1e-6:
        return float("inf")
    return landmark_distance(landmarks[4], landmarks[8]) / palm_scale


def finger_extended(landmarks: Sequence[Point], tip: int, pip: int) -> bool:
    """Detect extension by comparing tip and PIP distance from the wrist."""
    wrist = landmarks[0]
    return landmark_distance(landmarks[tip], wrist) > landmark_distance(landmarks[pip], wrist) * 1.05


class GestureInterpreter:
    """Classify the three gestures used by the isolated mouse feature."""

    def __init__(self, *, pinch_threshold: float = 0.22) -> None:
        self.pinch_threshold = pinch_threshold

    def interpret(self, landmarks: Sequence[Point]) -> GestureResult:
        if len(landmarks) < 21:
            raise ValueError("a MediaPipe hand must contain 21 landmarks")

        index_tip = landmarks[8]
        is_pinch = pinch_ratio(landmarks) < self.pinch_threshold
        if is_pinch:
            return GestureResult("pinch", True, index_tip.x, index_tip.y)

        index = finger_extended(landmarks, 8, 6)
        middle = finger_extended(landmarks, 12, 10)
        ring = finger_extended(landmarks, 16, 14)
        pinky = finger_extended(landmarks, 20, 18)

        if index and middle and not ring and not pinky:
            return GestureResult("scroll", False, index_tip.x, index_tip.y)
        if index and not middle and not ring and not pinky:
            return GestureResult("pointer", False, index_tip.x, index_tip.y)
        return GestureResult("idle", False, index_tip.x, index_tip.y)


class ClickLatch:
    """Translate pinch state into exactly one mouse-down and one mouse-up."""

    def __init__(self, emit) -> None:
        self._emit = emit
        self._held = False

    @property
    def held(self) -> bool:
        return self._held

    def update(self, pinching: bool) -> None:
        pinching = bool(pinching)
        if pinching and not self._held:
            self._emit("down")
            self._held = True
        elif not pinching and self._held:
            self._emit("up")
            self._held = False

    def release(self) -> None:
        if self._held:
            self._emit("up")
            self._held = False


class ScrollTracker:
    """Convert normalized vertical hand movement into scroll wheel units."""

    def __init__(self, *, gain: float = 180.0, deadzone: float = 0.01) -> None:
        self.gain = float(gain)
        self.deadzone = float(deadzone)
        self._last_y: float | None = None

    def reset(self) -> None:
        self._last_y = None

    def update(self, y: float) -> int:
        y = float(y)
        if self._last_y is None:
            self._last_y = y
            return 0
        delta = y - self._last_y
        if abs(delta) < self.deadzone:
            return 0
        self._last_y = y
        return int(round(-delta * self.gain))
