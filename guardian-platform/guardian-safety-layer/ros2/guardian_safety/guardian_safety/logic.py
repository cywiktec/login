"""ROS-independent logic of the guardian_safety nodes (testable without rclpy).

Fail-closed rules: missing, stale or non-finite input never counts as "safe".
Built on guardian_safety_layer (EmergencyStop, HeartbeatMonitor, Geofence, SafetyFSM, ...).
"""

import math
import time

from guardian_safety_layer.battery_guard import BatteryGuard, BatteryLevel
from guardian_safety_layer.estop import EmergencyStop
from guardian_safety_layer.geofence import Geofence
from guardian_safety_layer.risk_engine import RiskEngine
from guardian_safety_layer.safety_fsm import SafetyFSM, SafetyLevel
from guardian_safety_layer.watchdog import HeartbeatMonitor


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def require_positive(value, name):
    if not _finite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number, got {value!r}")
    return float(value)


def parse_polygon(flat):
    """[x1, y1, x2, y2, ...] -> [(x1, y1), ...]; raises ValueError if unset or malformed."""
    if flat is None:
        raise ValueError("polygon parameter is not set")
    values = list(flat)
    if len(values) < 6 or len(values) % 2:
        raise ValueError("polygon needs an even number of values (at least 3 vertices)")
    if not all(_finite(v) for v in values):
        raise ValueError("polygon contains non-finite values")
    return [(float(values[i]), float(values[i + 1])) for i in range(0, len(values), 2)]


class WatchdogLogic:
    """Supervises required heartbeat sources. A source that never reports expires too:
    registration at start gives it one timeout of grace."""

    def __init__(self, required_sources, timeout, clock=time.monotonic):
        sources = {str(s) for s in required_sources}
        if not sources:
            raise ValueError("required_sources must not be empty")
        self.required = tuple(sorted(sources))
        self._monitor = HeartbeatMonitor(require_positive(timeout, "timeout"), clock)
        for source in self.required:
            self._monitor.register(source)

    def beat(self, source):
        """Unlisted senders are ignored so they cannot mask a missing required source."""
        if source not in self.required:
            return False
        self._monitor.beat(source)
        return True

    def expired(self):
        return self._monitor.expired()

    def ok(self):
        return not self.expired()


class GeofenceLogic:
    def __init__(self, polygon, timeout, clock=time.monotonic):
        self.fence = Geofence(polygon)
        self.timeout = require_positive(timeout, "timeout")
        self._clock = clock
        self._position = None
        self._at = None

    def update(self, x, y):
        self._at = self._clock()
        self._position = (float(x), float(y)) if _finite(x) and _finite(y) else None

    def status(self):
        """ok | outside | no_position | stale | invalid. Only "ok" is safe."""
        if self._at is None:
            return "no_position"
        if self._clock() - self._at > self.timeout:
            return "stale"
        if self._position is None:
            return "invalid"
        return "ok" if self.fence.contains(*self._position) else "outside"

    def ok(self):
        return self.status() == "ok"


class EmergencyStopLogic:
    """Latching e-stop. Triggering is open to everyone; releasing needs `allow_reset`.
    There is no authentication yet, so `allow_reset` is the only guard."""

    def __init__(self, allow_reset=False):
        self.allow_reset = bool(allow_reset)
        self._estop = EmergencyStop()

    @property
    def active(self):
        return self._estop.active

    @property
    def reason(self):
        return self._estop.reason

    def trigger(self, reason):
        return self._estop.trigger(str(reason or "unspecified")[:200])

    def reset(self):
        if not self.allow_reset:
            raise PermissionError("reset is disabled (allow_reset=false)")
        self._estop.reset()


class SafetyManagerLogic:
    """Combines the estop, watchdog and geofence status plus battery into one SafetyLevel.

    - A status input that is missing or older than `input_timeout` counts as a fault, so a dead
      watchdog/geofence node degrades the system instead of silently passing.
    - SAFE_MODE and EMERGENCY_STOP latch in the FSM until `reset()`. WARNING does not latch.
    - During `startup_grace` (and only while some input was never seen) missing inputs show as
      SAFE_MODE but do not latch, so a slow boot needs no manual reset. An e-stop always latches.
    """

    INPUTS = ("estop", "watchdog", "geofence")

    def __init__(self, input_timeout=1.0, battery_timeout=10.0, startup_grace=5.0,
                 battery_low=30.0, battery_critical=15.0, clock=time.monotonic):
        self.input_timeout = require_positive(input_timeout, "input_timeout")
        self.battery_timeout = require_positive(battery_timeout, "battery_timeout")
        if not _finite(startup_grace) or startup_grace < 0:
            raise ValueError("startup_grace must be a finite number >= 0")
        self.startup_grace = float(startup_grace)
        self._clock = clock
        self._start = clock()
        self._guard = BatteryGuard(battery_low, battery_critical)
        self._risk = RiskEngine()
        self.fsm = SafetyFSM()
        self._inputs = {}
        self._battery = None

    def update_input(self, name, value):
        if name not in self.INPUTS:
            raise ValueError(f"unknown input: {name!r}")
        self._inputs[name] = (bool(value), self._clock())

    def update_battery(self, percent):
        valid = _finite(percent) and 0 <= percent <= 100
        self._battery = (float(percent) if valid else None, self._clock())

    def _fresh(self, name):
        entry = self._inputs.get(name)
        if entry is None or self._clock() - entry[1] > self.input_timeout:
            return None
        return entry[0]

    def _battery_level(self):
        if self._battery is None or self._battery[0] is None \
                or self._clock() - self._battery[1] > self.battery_timeout:
            return BatteryLevel.UNKNOWN
        return self._guard.evaluate(self._battery[0])

    def assess(self):
        """Level demanded right now, without latching."""
        estop = self._fresh("estop")
        watchdog = self._fresh("watchdog")
        geofence = self._fresh("geofence")
        level = self._risk.assess(
            estop_active=bool(estop),
            inside_geofence=bool(geofence),
            battery=self._battery_level(),
            expired_heartbeats=[] if watchdog else ["watchdog"],
        )
        if estop is None:
            level = max(level, SafetyLevel.SAFE_MODE)  # e-stop state unknown
        return level

    def _in_grace(self):
        return (self._clock() - self._start < self.startup_grace
                and any(name not in self._inputs for name in self.INPUTS))

    def evaluate(self):
        risk = self.assess()
        if risk is SafetyLevel.EMERGENCY_STOP or (risk >= SafetyLevel.SAFE_MODE and not self._in_grace()):
            self.fsm.escalate(risk)
        return max(self.fsm.level, risk)

    def reset(self):
        """Clears the latch only if every input is fresh and healthy right now.
        Returns (ok, message)."""
        risk = self.assess()
        if risk is not SafetyLevel.NORMAL:
            return False, f"conditions not normal: {risk.name}"
        self.fsm.clear_emergency_stop()
        self.fsm.reset()
        return True, "safety level reset to NORMAL"

    def status(self):
        return {"level": self.evaluate().name, "risk": self.assess().name,
                "latched": self.fsm.level.name, "battery": self._battery_level().name}
