"""Atomic, hash-verified snapshots stored as numbered generations."""

import json
import os
import re
import tempfile
import time

from ..hash import sha256_obj, verify

PATTERN = re.compile(r"^snapshot-(\d{10})\.json$")


class CorruptSnapshot(Exception):
    pass


def fsync_dir(directory):
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_atomic(path, data: bytes):
    """Write to a temp file in the same directory, fsync, then rename over the target.
    A crash leaves either the old file or the new one, never a partial file."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    fsync_dir(directory)


class SnapshotStore:
    def __init__(self, directory, clock=time.time):
        self.directory = directory
        self._clock = clock
        os.makedirs(directory, exist_ok=True)

    def path_for(self, seq):
        return os.path.join(self.directory, f"snapshot-{seq:010d}.json")

    def save(self, state, seq):
        if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
            raise ValueError("seq must be a non-negative integer")
        envelope = {"version": 1, "seq": seq, "created_at": self._clock(),
                    "sha256": sha256_obj(state), "state": state}
        data = json.dumps(envelope, sort_keys=True, allow_nan=False).encode("utf-8")
        path = self.path_for(seq)
        write_atomic(path, data)
        return path

    def load(self, seq):
        return self.load_path(self.path_for(seq))

    @staticmethod
    def load_path(path):
        try:
            with open(path, encoding="utf-8") as f:
                envelope = json.load(f)
            state = envelope["state"]
            if not verify(envelope["sha256"], sha256_obj(state)):
                raise CorruptSnapshot(f"hash mismatch: {path}")
            return envelope
        except CorruptSnapshot:
            raise
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise CorruptSnapshot(f"unreadable snapshot {path}: {error}") from error

    def list_seqs(self):
        found = []
        for name in os.listdir(self.directory):
            m = PATTERN.match(name)
            if m:
                found.append(int(m.group(1)))
        return sorted(found)

    def latest_valid(self):
        """Newest snapshot that verifies. Corrupt ones are skipped, never trusted."""
        for seq in reversed(self.list_seqs()):
            try:
                return self.load(seq)
            except CorruptSnapshot:
                continue
        return None
