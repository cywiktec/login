import tempfile
import unittest
from pathlib import Path

from guardian_core.recovery_manager import RecoveryManager
from guardian_core.snapshot_manager import SnapshotManager
from guardian_core.state_manager import GuardianState, StateManager


class RecoveryTests(unittest.TestCase):
    def test_recovery_restores_saved_state(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = StateManager()
            snapshots = SnapshotManager(Path(directory) / "state.json")
            manager.restore_state(GuardianState.READY)
            snapshots.save(manager)

            manager.restore_state(GuardianState.EMERGENCY_STOP)
            RecoveryManager(snapshots, manager).recover()

            self.assertIs(manager.state, GuardianState.READY)
