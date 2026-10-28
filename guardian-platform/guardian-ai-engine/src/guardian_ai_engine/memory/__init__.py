"""Bounded event memory."""

import threading
import time
from collections import deque


class Memory:
    def __init__(self, max_events=100, clock=time.time):
        if max_events < 1:
            raise ValueError("max_events must be at least 1")
        self._events = deque(maxlen=max_events)
        self._lock = threading.Lock()
        self._clock = clock

    def remember(self, kind, data=None):
        with self._lock:
            self._events.append({"at": self._clock(), "kind": kind, "data": data})

    def recent(self, n=10, kind=None):
        """Newest last."""
        with self._lock:
            events = [e for e in self._events if kind is None or e["kind"] == kind]
        return events[-n:] if n > 0 else []

    def last(self, kind):
        events = self.recent(1, kind)
        return events[0] if events else None

    def clear(self):
        with self._lock:
            self._events.clear()

    def __len__(self):
        return len(self._events)
