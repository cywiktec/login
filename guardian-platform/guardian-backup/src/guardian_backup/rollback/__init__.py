"""Non-destructive rollback: newer snapshots are moved aside, not deleted."""

import os

from ..snapshot import CorruptSnapshot, SnapshotStore

ROLLED_BACK = "rolled_back"


def rollback_to(store: SnapshotStore, seq):
    """Move every snapshot newer than `seq` into rolled_back/. The target must verify,
    otherwise nothing is moved. Returns the list of moved sequence numbers."""
    store.load(seq)  # raises CorruptSnapshot / unreadable before anything changes
    aside = os.path.join(store.directory, ROLLED_BACK)
    os.makedirs(aside, exist_ok=True)
    moved = []
    for s in store.list_seqs():
        if s > seq:
            os.replace(store.path_for(s), os.path.join(aside, os.path.basename(store.path_for(s))))
            moved.append(s)
    return moved


def restore_rolled_back(store: SnapshotStore):
    """Undo a rollback by moving the set-aside snapshots back."""
    aside = os.path.join(store.directory, ROLLED_BACK)
    if not os.path.isdir(aside):
        return []
    restored = []
    for name in sorted(os.listdir(aside)):
        target = os.path.join(store.directory, name)
        if not os.path.exists(target):
            os.replace(os.path.join(aside, name), target)
            restored.append(name)
    return restored
