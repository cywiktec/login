"""Heartbeat supervision for multiple sources, with an injectable clock."""

import threading
import time


class HeartbeatMonitor:
    def __init__(self, timeout, clock=time.monotonic):
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.timeout = timeout
        self._clock = clock
        self._lock = threading.Lock()
        self._last = {}

    def register(self, source):
        self.beat(source)

    def beat(self, source):
        with self._lock:
            self._last[source] = self._clock()

    def expired(self):
        """Sources whose last heartbeat is older than the timeout."""
        now = self._clock()
        with self._lock:
            return sorted(s for s, t in self._last.items() if now - t > self.timeout)
