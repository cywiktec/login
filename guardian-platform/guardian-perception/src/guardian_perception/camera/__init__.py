"""Camera frame metadata validation and freshness. Pixel data is opaque bytes."""

import math
import time
from dataclasses import dataclass


class FrameError(ValueError):
    pass


@dataclass(frozen=True)
class Frame:
    width: int
    height: int
    ts: float
    data: bytes = b""
    encoding: str = "rgb8"


_BYTES_PER_PIXEL = {"rgb8": 3, "bgr8": 3, "mono8": 1}


def make_frame(width, height, ts, data=b"", encoding="rgb8"):
    for name, v in (("width", width), ("height", height)):
        if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
            raise FrameError(f"{name} must be a positive integer")
    if isinstance(ts, bool) or not isinstance(ts, (int, float)) or not math.isfinite(ts):
        raise FrameError("ts must be finite")
    if encoding not in _BYTES_PER_PIXEL:
        raise FrameError(f"unsupported encoding: {encoding!r}")
    if data and len(data) != width * height * _BYTES_PER_PIXEL[encoding]:
        raise FrameError("data length does not match dimensions")
    return Frame(width, height, float(ts), bytes(data), encoding)


class CameraSource:
    """Holds the latest frame; `latest()` returns None when it is missing or stale."""

    def __init__(self, max_age=0.5, clock=time.monotonic):
        self.max_age = max_age
        self._clock = clock
        self._frame = None
        self._received = None

    def push(self, frame):
        if not isinstance(frame, Frame):
            raise FrameError("not a Frame")
        if self._frame is not None and frame.ts <= self._frame.ts:
            return False  # out-of-order or duplicate frame
        self._frame, self._received = frame, self._clock()
        return True

    def latest(self):
        if self._frame is None or self._clock() - self._received > self.max_age:
            return None
        return self._frame
