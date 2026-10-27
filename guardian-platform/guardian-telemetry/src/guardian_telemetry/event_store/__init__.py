"""Append-only JSON Lines event store. Corrupt lines are skipped and counted, never fatal."""

import json
import os
import threading

from ..message import MessageError, make_message


class EventStore:
    def __init__(self, path, max_bytes=50 * 1024 * 1024, fsync=False):
        self.path = path
        self.max_bytes = max_bytes
        self.fsync = fsync
        self.skipped = 0
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    def append(self, msg):
        """Returns False (and stores nothing) when the store is full; callers must not
        assume persistence. Rotation/archival is left to guardian-backup."""
        line = (json.dumps({"robot_id": msg.robot_id, "kind": msg.kind, "ts": msg.ts,
                            "data": msg.data}, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
        with self._lock:
            size = os.path.getsize(self.path) if os.path.exists(self.path) else 0
            if size + len(line) > self.max_bytes:
                return False
            with open(self.path, "ab") as f:
                f.write(line)
                f.flush()
                if self.fsync:
                    os.fsync(f.fileno())
        return True

    def query(self, robot_id=None, kind=None, since=None, until=None, limit=1000):
        out, skipped = [], 0
        if not os.path.exists(self.path):
            return out
        with open(self.path, "rb") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    msg = make_message(obj["robot_id"], obj["kind"], obj["ts"], obj["data"])
                except (ValueError, KeyError, TypeError, MessageError):
                    skipped += 1
                    continue
                if robot_id is not None and msg.robot_id != robot_id:
                    continue
                if kind is not None and msg.kind != kind:
                    continue
                if since is not None and msg.ts < since:
                    continue
                if until is not None and msg.ts > until:
                    continue
                out.append(msg)
        self.skipped = skipped
        return out[-limit:] if limit else []
