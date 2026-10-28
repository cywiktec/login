"""Snapshot retention: keep the newest N and anything recent; never the last valid one."""

import os
import time

from ..snapshot import PATTERN, CorruptSnapshot, SnapshotStore


def apply_retention(store: SnapshotStore, keep_last=5, max_age_s=None, now=None):
    """Delete old snapshot files. Only files matching the snapshot pattern are touched.
    The newest snapshot that verifies is always kept, even beyond the limits.
    Returns the deleted sequence numbers."""
    if keep_last < 1:
        raise ValueError("keep_last must be at least 1")
    now = time.time() if now is None else now
    seqs = store.list_seqs()
    protected = set(seqs[-keep_last:])
    latest = store.latest_valid()
    if latest is not None:
        protected.add(latest["seq"])

    deleted = []
    for seq in seqs:
        if seq in protected:
            continue
        path = store.path_for(seq)
        if max_age_s is not None and now - os.path.getmtime(path) <= max_age_s:
            continue
        os.unlink(path)
        deleted.append(seq)
    return deleted
