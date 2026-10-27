from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

LOGGER = logging.getLogger("misiek.recovery")

DEFAULT_MIN_HEALTH = 80.0  # placeholder threshold


class RecoveryState(Enum):
    INIT = "INIT"
    JOURNAL_SCAN = "JOURNAL_SCAN"
    SNAPSHOT_VERIFY = "SNAPSHOT_VERIFY"
    SNAPSHOT_RESTORE = "SNAPSHOT_RESTORE"
    JOURNAL_REPLAY = "JOURNAL_REPLAY"
    MISSION_RESTORE = "MISSION_RESTORE"
    HEALTH_CHECK = "HEALTH_CHECK"
    READY = "READY"
    FAILED = "FAILED"


@dataclass
class RecoveryReport:
    success: bool
    snapshot_file: Optional[str]
    journal_entries: int
    mission_restored: bool
    health_score: float
    state: str


class RecoveryEngine:
    """Snapshot + journal recovery. Fails closed: any problem ends in FAILED, never READY.

    The latest snapshot whose schema and `<snapshot>.sha256` both check out is used; older
    valid snapshots are the fallback. Journal entries are replayed through `apply` (if given).
    """

    REQUIRED_FIELDS = ["snapshot_id", "created_utc", "state"]

    def __init__(
        self,
        snapshot_dir="snapshots/mission",
        journal_dir="journal",
        apply: Optional[Callable[[dict], None]] = None,
        health_check: Optional[Callable[[], float]] = None,
        min_health: float = DEFAULT_MIN_HEALTH,
    ):
        self.snapshot_dir = Path(snapshot_dir)
        self.journal_dir = Path(journal_dir)
        self.apply = apply
        self.health_check = health_check or self._default_health_check
        self.min_health = min_health
        self.state = RecoveryState.INIT

    def run(self) -> RecoveryReport:
        snapshot_name = None
        journal_count = 0
        try:
            self.state = RecoveryState.JOURNAL_SCAN
            entries = self._scan_journal()
            journal_count = len(entries)

            self.state = RecoveryState.SNAPSHOT_VERIFY
            snapshot = self._find_latest_valid_snapshot()
            if snapshot is None:
                LOGGER.error("No valid snapshot found")
                return self._failed()
            snapshot_name = snapshot.name

            self.state = RecoveryState.SNAPSHOT_RESTORE
            data = self._restore_snapshot(snapshot)

            self.state = RecoveryState.JOURNAL_REPLAY
            self._replay_journal(entries)

            self.state = RecoveryState.MISSION_RESTORE
            mission_restored = self._restore_mission(data)

            self.state = RecoveryState.HEALTH_CHECK
            score = float(self.health_check())
            if not score >= self.min_health:  # also rejects NaN
                LOGGER.error("Health score %s below %s", score, self.min_health)
                return self._failed(snapshot_name, journal_count, mission_restored, score)

            self.state = RecoveryState.READY
            return RecoveryReport(True, snapshot_name, journal_count, mission_restored,
                                  score, self.state.value)
        except Exception:
            LOGGER.exception("Recovery engine failed")
            return self._failed(snapshot_name, journal_count)

    def _failed(self, snapshot_file=None, journal_entries=0, mission_restored=False, score=0.0):
        self.state = RecoveryState.FAILED
        return RecoveryReport(False, snapshot_file, journal_entries, mission_restored,
                              score, self.state.value)

    def _scan_journal(self):
        entries = sorted(self.journal_dir.glob("*.json"))
        LOGGER.info("Journal entries found: %s", len(entries))
        return entries

    def _replay_journal(self, entries):
        """A corrupt entry raises, which fails the whole recovery."""
        for entry in entries:
            with open(entry, "r", encoding="utf-8") as f:
                tx = json.load(f)
            if not isinstance(tx, dict) or not tx.get("tx_id"):
                raise ValueError(f"journal entry without tx_id: {entry.name}")
            LOGGER.info("Replay TX: %s", tx["tx_id"])
            if self.apply is not None:
                self.apply(tx)

    def _find_latest_valid_snapshot(self):
        # Names are expected to sort chronologically (e.g. a UTC timestamp in the name).
        snapshots = sorted(self.snapshot_dir.glob("MISIEK-SNAPSHOT-*.json"), reverse=True)
        for snap in snapshots:
            if self._verify_snapshot(snap):
                return snap
        return None

    def _restore_snapshot(self, snapshot):
        with open(snapshot, "r", encoding="utf-8") as f:
            data = json.load(f)
        LOGGER.info("Snapshot restored: %s", snapshot.name)
        return data

    def _verify_snapshot(self, snapshot) -> bool:
        return self._verify_schema(snapshot) and self._verify_sha256(snapshot)

    def _verify_schema(self, snapshot) -> bool:
        try:
            with open(snapshot, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return False
        if not isinstance(data, dict):
            return False
        for field in self.REQUIRED_FIELDS:
            if field not in data:
                LOGGER.warning("Missing field: %s", field)
                return False
        return True

    def _verify_sha256(self, snapshot) -> bool:
        sha_file = Path(str(snapshot) + ".sha256")
        try:
            # Accepts both "<hash>" and sha256sum's "<hash>  <name>".
            expected = sha_file.read_text().split()[0].lower()
            calculated = self._calculate_sha256(snapshot)
        except (OSError, IndexError):
            return False
        return hmac.compare_digest(expected, calculated)

    @staticmethod
    def _calculate_sha256(file_path):
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def _restore_mission(self, snapshot_data) -> bool:
        """`state` must be an object for a mission to exist; the plain-string state written by
        guardian_core.SnapshotManager has no mission, so it restores nothing (False)."""
        state = snapshot_data["state"]
        if not isinstance(state, dict):
            return False
        mission = state.get("mission")
        LOGGER.info("Mission restore: %s", mission)
        LOGGER.info("Waypoint restore: %s", state.get("current_waypoint"))
        return mission is not None

    def _default_health_check(self) -> float:
        """Placeholder: only checks that the snapshot directory is readable. Inject a real
        `health_check` (e.g. from guardian_core.health) for anything meaningful."""
        return 100.0 if self.snapshot_dir.is_dir() else 0.0
