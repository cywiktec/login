"""Recover state after a crash: latest valid snapshot + journal replay, then a resume plan."""

import time
from dataclasses import dataclass
from typing import Optional

from ..journaling import Journal
from ..snapshot import SnapshotStore


@dataclass(frozen=True)
class Recovered:
    state: dict
    last_seq: int
    snapshot_seq: int
    replayed: int
    journal_damaged: bool


def recover_state(store: SnapshotStore, journal: Journal, apply):
    """apply(state, data) -> new state. Entries after the snapshot are replayed in order.
    Returns None if there is no valid snapshot (callers must start from a safe default)."""
    snap = store.latest_valid()
    if snap is None:
        return None
    state, seq = snap["state"], snap["seq"]
    replayed = 0
    for entry in journal.entries(after_seq=seq):
        state = apply(state, entry["data"])
        seq = entry["seq"]
        replayed += 1
    return Recovered(state, seq, snap["seq"], replayed, journal.damaged)


@dataclass(frozen=True)
class ResumePlan:
    action: str  # "resume", "none" or "manual"
    reason: str
    checkpoint: Optional[dict] = None


def plan_auto_resume(recovered, saved_at, enabled=True, max_age_s=300.0, now=None,
                     mission_states=("MISSION", "RTB")):
    """Decide whether an interrupted mission may be resumed automatically.

    This only *proposes*. The caller must still run the proposal through the
    state machine and safety layer. Fails closed: damaged journal, stale data or a
    missing checkpoint never yield "resume"."""
    now = time.time() if now is None else now
    if recovered is None:
        return ResumePlan("manual", "no valid snapshot")
    state = recovered.state
    if state.get("state") not in mission_states:
        return ResumePlan("none", "no mission was in progress")
    if not enabled:
        return ResumePlan("manual", "auto resume disabled")
    if recovered.journal_damaged:
        return ResumePlan("manual", "journal damaged; operator must confirm")
    if not isinstance(saved_at, (int, float)) or now - saved_at > max_age_s:
        return ResumePlan("manual", "state too old to resume automatically")
    checkpoint = state.get("checkpoint")
    if not isinstance(checkpoint, dict):
        return ResumePlan("manual", "no mission checkpoint")
    return ResumePlan("resume", "mission interrupted with a fresh checkpoint", checkpoint)
