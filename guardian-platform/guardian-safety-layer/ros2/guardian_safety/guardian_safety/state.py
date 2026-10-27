"""Operator-facing safety state machine (MONITORING .. E_STOP).

Rules:
- Setters only escalate. A lower request is ignored (returns False), never a downgrade.
- E_STOP is terminal until `reset()`, which needs `allow_reset` and goes back to MONITORING.
- Every transition is recorded in `history` (audit trail, bounded).

Assumed meaning (not specified by the spec, please confirm):
  MONITORING = normal, DEGRADED = non-critical problem (e.g. low battery),
  FAILSAFE   = a safety input is lost/stale, hold position,
  SAFE_MODE  = motion disabled, latched, E_STOP = emergency stop latched.
"""

import time
from enum import Enum

from guardian_safety_layer.safety_fsm import SafetyLevel


class SafetyState(Enum):
    MONITORING = 0
    DEGRADED = 1
    FAILSAFE = 2
    SAFE_MODE = 3
    E_STOP = 4


_FROM_LEVEL = {
    SafetyLevel.NORMAL: SafetyState.MONITORING,
    SafetyLevel.WARNING: SafetyState.DEGRADED,
    SafetyLevel.SAFE_MODE: SafetyState.SAFE_MODE,
    SafetyLevel.EMERGENCY_STOP: SafetyState.E_STOP,
}


def from_level(level):
    """Maps the safety manager node's SafetyLevel to a SafetyState."""
    return _FROM_LEVEL[SafetyLevel(level)]


class SafetyManager:
    MAX_HISTORY = 1000

    def __init__(self, allow_reset=False, clock=time.time):
        self.allow_reset = bool(allow_reset)
        self._clock = clock
        self.state = SafetyState.MONITORING
        self.history = []

    def _escalate(self, target, reason):
        if target.value <= self.state.value:
            return False
        self._record(target, reason)
        return True

    def _record(self, target, reason):
        self.history.append((self._clock(), self.state.name, target.name, str(reason)))
        del self.history[:-self.MAX_HISTORY]
        self.state = target

    def set_degraded(self, reason="unspecified"):
        return self._escalate(SafetyState.DEGRADED, reason)

    def set_failsafe(self, reason="unspecified"):
        return self._escalate(SafetyState.FAILSAFE, reason)

    def set_safe_mode(self, reason="unspecified"):
        return self._escalate(SafetyState.SAFE_MODE, reason)

    def trigger_estop(self, reason="unspecified"):
        return self._escalate(SafetyState.E_STOP, reason)

    def apply_level(self, level, reason="level"):
        return self._escalate(from_level(level), reason)

    def clear_degraded(self):
        """DEGRADED is the only state that clears by itself (the cause went away)."""
        if self.state is SafetyState.DEGRADED:
            self._record(SafetyState.MONITORING, "degraded cleared")
            return True
        return False

    @property
    def motion_allowed(self):
        return self.state in (SafetyState.MONITORING, SafetyState.DEGRADED)

    def reset(self):
        if not self.allow_reset:
            raise PermissionError("reset is disabled (allow_reset=false)")
        if self.state is SafetyState.MONITORING:
            return False
        self._record(SafetyState.MONITORING, "reset")
        return True


def main():
    manager = SafetyManager()
    print(manager.state)
