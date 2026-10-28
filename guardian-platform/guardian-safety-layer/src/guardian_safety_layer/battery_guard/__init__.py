"""Battery threshold evaluation."""

from enum import Enum


class BatteryLevel(Enum):
    UNKNOWN = "UNKNOWN"
    OK = "OK"
    LOW = "LOW"
    CRITICAL = "CRITICAL"


class BatteryGuard:
    def __init__(self, low=30.0, critical=15.0):
        if not 0 <= critical < low <= 100:
            raise ValueError("require 0 <= critical < low <= 100")
        self.low = low
        self.critical = critical

    def evaluate(self, percent, plugged=False):
        # Missing data is reported as UNKNOWN, never assumed healthy.
        if percent is None:
            return BatteryLevel.UNKNOWN
        if percent <= self.critical and not plugged:
            return BatteryLevel.CRITICAL
        if percent <= self.low and not plugged:
            return BatteryLevel.LOW
        return BatteryLevel.OK
