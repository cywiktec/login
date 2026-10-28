"""Latest-value cache per robot and kind, with staleness."""

import threading
import time


class SnapshotCache:
    def __init__(self, clock=time.time):
        self._clock = clock
        self._lock = threading.Lock()
        self._latest = {}  # (robot_id, kind) -> (received_at, message)

    def update(self, msg):
        """Older messages (by message timestamp) never overwrite newer ones."""
        key = (msg.robot_id, msg.kind)
        with self._lock:
            current = self._latest.get(key)
            if current is not None and msg.ts < current[1].ts:
                return False
            self._latest[key] = (self._clock(), msg)
            return True

    def get(self, robot_id, kind, max_age=None):
        """Latest message, or None if unknown or older than max_age seconds since receipt."""
        with self._lock:
            entry = self._latest.get((robot_id, kind))
        if entry is None:
            return None
        if max_age is not None and self._clock() - entry[0] > max_age:
            return None
        return entry[1]

    def snapshot(self, robot_id, max_age=None):
        out = {}
        with self._lock:
            keys = [k for k in self._latest if k[0] == robot_id]
        for _, kind in keys:
            msg = self.get(robot_id, kind, max_age)
            if msg is not None:
                out[kind] = msg
        return out

    def robots(self):
        with self._lock:
            return sorted({k[0] for k in self._latest})
