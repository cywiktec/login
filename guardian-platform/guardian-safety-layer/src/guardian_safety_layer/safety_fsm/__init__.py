"""Safety state machine: levels only escalate until explicitly reset."""

from enum import IntEnum


class SafetyLevel(IntEnum):
    NORMAL = 0
    WARNING = 1
    SAFE_MODE = 2
    EMERGENCY_STOP = 3


class SafetyFSM:
    def __init__(self):
        self._level = SafetyLevel.NORMAL

    @property
    def level(self):
        return self._level

    def escalate(self, level):
        """Raise the level; requests lower than the current level are ignored."""
        level = SafetyLevel(level)
        if level > self._level:
            self._level = level
        return self._level

    def reset(self):
        """Return to NORMAL. EMERGENCY_STOP is latched and cannot be reset here."""
        if self._level is SafetyLevel.EMERGENCY_STOP:
            raise PermissionError("EMERGENCY_STOP must be cleared explicitly")
        self._level = SafetyLevel.NORMAL

    def clear_emergency_stop(self):
        if self._level is SafetyLevel.EMERGENCY_STOP:
            self._level = SafetyLevel.NORMAL
