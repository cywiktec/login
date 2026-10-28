"""Robot telemetry as seen by the app, with staleness: old data is never shown as current."""

import math
import time
from dataclasses import dataclass
from typing import Optional

STATES = {"INIT", "SELF_TEST", "READY", "MISSION", "RTB", "CHARGING", "SAFE_MODE", "EMERGENCY_STOP"}


@dataclass(frozen=True)
class Telemetry:
    state: str
    battery_pct: Optional[float]
    x: Optional[float] = None
    y: Optional[float] = None
    received_at: float = 0.0


def parse_telemetry(data, now):
    """Dict from the API -> Telemetry, or None if it is not trustworthy."""
    if not isinstance(data, dict) or data.get("state") not in STATES:
        return None

    def number(key, low=None, high=None):
        v = data.get(key)
        if v is None:
            return None
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(key)
        if low is not None and not low <= v <= high:
            raise ValueError(key)
        return float(v)

    try:
        return Telemetry(data["state"], number("battery_pct", 0, 100),
                         number("x"), number("y"), now)
    except ValueError:
        return None


class TelemetryView:
    def __init__(self, stale_after=5.0, clock=time.monotonic):
        self.stale_after = stale_after
        self._clock = clock
        self._latest = None

    def update(self, data):
        """Returns True if accepted. Rejected data leaves the previous value to age out."""
        parsed = parse_telemetry(data, self._clock())
        if parsed is None:
            return False
        self._latest = parsed
        return True

    @property
    def latest(self):
        return self._latest

    @property
    def stale(self):
        return self._latest is None or self._clock() - self._latest.received_at > self.stale_after

    def status(self):
        """'no_data', 'stale' or 'live'."""
        if self._latest is None:
            return "no_data"
        return "stale" if self.stale else "live"
