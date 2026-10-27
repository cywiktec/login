"""Latching emergency stop."""

import threading


class EmergencyStop:
    def __init__(self):
        self._lock = threading.Lock()
        self._active = False
        self._reason = None
        self._listeners = []

    @property
    def active(self):
        return self._active

    @property
    def reason(self):
        return self._reason

    def on_trigger(self, callback):
        self._listeners.append(callback)

    def trigger(self, reason):
        with self._lock:
            if self._active:
                return False
            self._active = True
            self._reason = reason

        for callback in self._listeners:
            callback(reason)
        return True

    def reset(self):
        """Release the latch. Callers must enforce authorization before calling."""
        with self._lock:
            self._active = False
            self._reason = None
