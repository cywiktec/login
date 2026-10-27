"""Parse raw robot state into validated telemetry, tracking freshness."""

import math
import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Telemetry:
    battery_percent: float
    charging: bool
    position: tuple
    velocity: tuple
    received_at: float


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def parse_state(raw, now):
    """Build Telemetry from a raw dict; raises ValueError on malformed data."""
    if not isinstance(raw, dict):
        raise ValueError("state must be a dict")
    percent = _finite(raw.get("battery_percent"), "battery_percent")
    if not 0 <= percent <= 100:
        raise ValueError("battery_percent must be within 0-100")
    return Telemetry(
        battery_percent=percent,
        charging=bool(raw.get("charging", False)),
        position=tuple(_finite(v, "position") for v in raw.get("position", (0, 0, 0))),
        velocity=tuple(_finite(v, "velocity") for v in raw.get("velocity", (0, 0, 0))),
        received_at=now,
    )


class TelemetryCollector:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._latest = None
        self.rejected = 0

    def handle(self, raw):
        """Subscriber callback. Malformed messages are counted and dropped."""
        try:
            telemetry = parse_state(raw, self._clock())
        except ValueError:
            with self._lock:
                self.rejected += 1
            return
        with self._lock:
            self._latest = telemetry

    def latest(self, max_age=None):
        """Latest telemetry, or None if absent or older than max_age seconds."""
        with self._lock:
            telemetry = self._latest
        if telemetry is None:
            return None
        if max_age is not None and self._clock() - telemetry.received_at > max_age:
            return None
        return telemetry
