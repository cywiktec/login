import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from guardian_core.command_dispatcher import CommandDispatcher, normalize
from guardian_core.guardian_node import GuardianNode
from guardian_core.recovery_manager import RecoveryManager
from guardian_core.snapshot_manager import SnapshotManager
from guardian_core.state_manager import GuardianState, StateManager


class FakeHealth:
    def get_status(self):
        return {"cpu": 1.0, "ram": 2.0, "disk": 3.0}

    def get_battery(self):
        return {"percent": 80, "plugged": False}


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sm = StateManager()
        snaps = SnapshotManager(Path(self.tmp.name) / "s.json")
        self.node = GuardianNode(
            self.sm, None, FakeHealth(), snaps, RecoveryManager(snaps, self.sm)
        )
        self.node.initialize()
        self.dispatcher = CommandDispatcher(self.node)

    def run_cmd(self, command):
        out = StringIO()
        with redirect_stdout(out):
            self.dispatcher.execute(command)
        return out.getvalue()

    def test_normalize(self):
        self.assertEqual(normalize("MISIEK, wróć do bazy."), "wroc do bazy")
        self.assertEqual(normalize("MISIEK, wznów po awarii."), "wznow po awarii")

    def test_patrol_abort_and_return(self):
        self.run_cmd("MISIEK, rozpocznij patrol.")
        self.assertIs(self.sm.state, GuardianState.MISSION)
        self.run_cmd("MISIEK, zatrzymaj misję.")
        self.assertIs(self.sm.state, GuardianState.READY)
        self.run_cmd("MISIEK, rozpocznij patrol.")
        self.run_cmd("MISIEK, wróć do bazy.")
        self.assertIs(self.sm.state, GuardianState.RTB)

    def test_abort_without_mission(self):
        self.assertIn("brak aktywnej misji", self.run_cmd("MISIEK, zatrzymaj misję."))

    def test_battery_and_diagnostics(self):
        self.assertIn("80%", self.run_cmd("MISIEK, poziom baterii."))
        self.assertIn("[DIAG]", self.run_cmd("MISIEK, uruchom diagnostykę."))

    def test_snapshot_and_recovery(self):
        self.run_cmd("MISIEK, rozpocznij patrol.")
        self.run_cmd("MISIEK, wykonaj snapshot.")
        self.run_cmd("stop")
        self.assertIs(self.sm.state, GuardianState.EMERGENCY_STOP)
        self.run_cmd("MISIEK, wznow po awarii.")
        self.assertIs(self.sm.state, GuardianState.MISSION)

    def test_recovery_without_snapshot(self):
        self.assertIn("brak snapshotu", self.run_cmd("MISIEK, wznow po awarii."))

    def test_unknown(self):
        self.assertIn("nierozpoznana", self.run_cmd("MISIEK, tańcz"))


class BatteryTests(unittest.TestCase):
    def test_missing_power_supply_returns_none(self):
        from unittest.mock import patch

        from guardian_core.health import HealthMonitor

        with patch("psutil.sensors_battery", side_effect=FileNotFoundError):
            self.assertIsNone(HealthMonitor().get_battery())
