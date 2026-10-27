"""Velocity control with limits, validation and a command deadman."""

import math
import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    max_linear: float = 0.5
    max_lateral: float = 0.3
    max_angular: float = 1.0


class Controller:
    def __init__(self, bridge, limits=Limits(), command_timeout=0.5, clock=time.monotonic):
        if command_timeout <= 0:
            raise ValueError("command_timeout must be positive")
        self.bridge = bridge
        self.limits = limits
        self.command_timeout = command_timeout
        self._clock = clock
        self._lock = threading.Lock()
        self._stopped = False
        self._last_command_at = None
        self._moving = False

    @staticmethod
    def _clamp(value, limit):
        return max(-limit, min(limit, value))

    def move(self, vx, vy, wz):
        """Send a velocity command, clamped to limits. Non-finite input is rejected."""
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (vx, vy, wz)):
            raise ValueError("velocities must be finite numbers")
        with self._lock:
            if self._stopped:
                return False
            command = (
                self._clamp(vx, self.limits.max_linear),
                self._clamp(vy, self.limits.max_lateral),
                self._clamp(wz, self.limits.max_angular),
            )
            self._last_command_at = self._clock()
            self._moving = any(command)
        self.bridge.send_sport_request({"api": "Move", "vx": command[0], "vy": command[1], "wz": command[2]})
        return True

    def stop(self):
        """Stop motion; always sent, even when latched."""
        with self._lock:
            self._moving = False
        self.bridge.send_sport_request({"api": "StopMove"})

    def emergency_stop(self):
        """Latch: stop, then ignore move() until release()."""
        with self._lock:
            self._stopped = True
        self.stop()

    def release(self):
        with self._lock:
            self._stopped = False

    @property
    def latched(self):
        return self._stopped

    def tick(self):
        """Call periodically: stops the robot if commands went stale. Returns True if it did."""
        with self._lock:
            stale = (
                self._moving
                and self._last_command_at is not None
                and self._clock() - self._last_command_at > self.command_timeout
            )
        if stale:
            self.stop()
        return stale
