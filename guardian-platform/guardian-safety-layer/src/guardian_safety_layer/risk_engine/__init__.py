"""Combine safety signals into a single SafetyLevel."""

from ..battery_guard import BatteryLevel
from ..safety_fsm import SafetyLevel


class RiskEngine:
    def assess(self, *, estop_active, inside_geofence, battery, expired_heartbeats):
        """Return the highest level demanded by any signal.

        inside_geofence=None (position unknown) is treated as a violation.
        """
        if estop_active:
            return SafetyLevel.EMERGENCY_STOP

        level = SafetyLevel.NORMAL
        if battery is BatteryLevel.CRITICAL or not inside_geofence:
            level = max(level, SafetyLevel.SAFE_MODE)
        if expired_heartbeats:
            level = max(level, SafetyLevel.SAFE_MODE)
        if battery in (BatteryLevel.LOW, BatteryLevel.UNKNOWN):
            level = max(level, SafetyLevel.WARNING)
        return level
