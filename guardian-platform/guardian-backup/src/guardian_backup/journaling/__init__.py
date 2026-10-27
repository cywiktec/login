"""Append-only journal with a hash chain; a torn or tampered tail is detected."""

import json
import os
import time

from ..hash import sha256_obj, verify
from ..snapshot import fsync_dir

GENESIS = "0" * 64


class Journal:
    def __init__(self, path, clock=time.time):
        self.path = path
        self._clock = clock
        entries, good_bytes, self.damaged = self._scan()
        if self.damaged:
            # Drop the damaged tail so new entries chain onto the last valid one.
            with open(path, "r+b") as f:
                f.truncate(good_bytes)
        self._last_seq = entries[-1]["seq"] if entries else 0
        self._last_hash = entries[-1]["hash"] if entries else GENESIS
        new_file = not os.path.exists(path)
        self._file = open(path, "ab")
        if new_file:
            fsync_dir(os.path.dirname(os.path.abspath(path)))

    @property
    def last_seq(self):
        return self._last_seq

    def append(self, data):
        entry = {"seq": self._last_seq + 1, "ts": self._clock(), "data": data, "prev": self._last_hash}
        entry["hash"] = sha256_obj({k: entry[k] for k in ("seq", "ts", "data", "prev")})
        line = json.dumps(entry, sort_keys=True, allow_nan=False) + "\n"
        self._file.write(line.encode("utf-8"))
        self._file.flush()
        os.fsync(self._file.fileno())
        self._last_seq, self._last_hash = entry["seq"], entry["hash"]
        return entry["seq"]

    def entries(self, after_seq=0):
        entries, _, _ = self._scan()
        return [e for e in entries if e["seq"] > after_seq]

    def close(self):
        self._file.close()

    def __del__(self):
        f = getattr(self, "_file", None)
        if f is not None and not f.closed:
            f.close()

    def _scan(self):
        """Return (valid entries, byte length of the valid prefix, damaged?)."""
        entries, good, prev = [], 0, GENESIS
        if not os.path.exists(self.path):
            return entries, 0, False
        with open(self.path, "rb") as f:
            raw = f.read()
        offset = 0
        for line in raw.splitlines(keepends=True):
            try:
                if not line.endswith(b"\n"):
                    raise ValueError("torn line")
                e = json.loads(line)
                body = {k: e[k] for k in ("seq", "ts", "data", "prev")}
                ok = (e["prev"] == prev and e["seq"] == len(entries) + 1
                      and verify(e["hash"], sha256_obj(body)))
            except (ValueError, KeyError, TypeError):
                ok = False
            if not ok:
                return entries, good, True
            entries.append(e)
            prev = e["hash"]
            offset += len(line)
            good = offset
        return entries, good, False
