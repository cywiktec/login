import tempfile
import unittest
from pathlib import Path

from guardian_core.snapshot_manager import SnapshotManager
from guardian_core.state_manager import GuardianState, StateManager


class SnapshotTests(unittest.TestCase):
    def test_save_and_restore_state(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = StateManager()
            manager.restore_state(GuardianState.MISSION)
            snapshots = SnapshotManager(Path(directory) / "state.json")
            snapshots.save(manager)

            manager.restore_state(GuardianState.EMERGENCY_STOP)
            snapshots.restore(manager)

            self.assertIs(manager.state, GuardianState.MISSION)
