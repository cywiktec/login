import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from guardian_core.recovery_engine import RecoveryEngine


def write_snapshot(directory, name, state, sha=True, **extra):
    path = Path(directory) / f"MISIEK-SNAPSHOT-{name}.json"
    data = {"snapshot_id": name, "created_utc": "2026-01-01T00:00:00Z", "state": state, **extra}
    path.write_text(json.dumps(data))
    if sha:
        Path(str(path) + ".sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest() + "  x\n")
    return path


class RecoveryEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.snaps = Path(self.tmp.name) / "snaps"
        self.journal = Path(self.tmp.name) / "journal"
        self.snaps.mkdir()
        self.journal.mkdir()

    def engine(self, **kw):
        return RecoveryEngine(self.snaps, self.journal, **kw)

    def test_success_with_mission(self):
        write_snapshot(self.snaps, "001", {"mission": "patrol", "current_waypoint": 3})
        r = self.engine().run()
        self.assertTrue(r.success)
        self.assertTrue(r.mission_restored)
        self.assertEqual((r.state, r.snapshot_file), ("READY", "MISIEK-SNAPSHOT-001.json"))

    def test_no_snapshot_fails(self):
        r = self.engine().run()
        self.assertFalse(r.success)
        self.assertEqual(r.state, "FAILED")

    def test_missing_directories_fail_not_crash(self):
        r = RecoveryEngine(Path(self.tmp.name) / "nope", Path(self.tmp.name) / "nada").run()
        self.assertFalse(r.success)

    def test_falls_back_past_tampered_and_unhashed_snapshots(self):
        write_snapshot(self.snaps, "001", {"mission": "old"})
        bad = write_snapshot(self.snaps, "002", {"mission": "new"})
        bad.write_text(bad.read_text() + " ")                      # tampered after hashing
        write_snapshot(self.snaps, "003", {"mission": "x"}, sha=False)
        r = self.engine().run()
        self.assertTrue(r.success)
        self.assertEqual(r.snapshot_file, "MISIEK-SNAPSHOT-001.json")

    def test_schema_failures(self):
        for content in ("{", "[]", json.dumps({"snapshot_id": "1"})):
            path = self.snaps / "MISIEK-SNAPSHOT-9.json"
            path.write_text(content)
            Path(str(path) + ".sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertFalse(self.engine().run().success, content)

    def test_empty_sha_file_is_invalid(self):
        path = write_snapshot(self.snaps, "001", {})
        Path(str(path) + ".sha256").write_text("")
        self.assertFalse(self.engine().run().success)

    def test_string_state_from_snapshot_manager_restores_no_mission(self):
        write_snapshot(self.snaps, "001", "READY")
        r = self.engine().run()
        self.assertTrue(r.success)
        self.assertFalse(r.mission_restored)

    def test_journal_replayed_in_order_via_apply(self):
        write_snapshot(self.snaps, "001", {})
        (self.journal / "b.json").write_text(json.dumps({"tx_id": "2"}))
        (self.journal / "a.json").write_text(json.dumps({"tx_id": "1"}))
        seen = []
        r = self.engine(apply=lambda tx: seen.append(tx["tx_id"])).run()
        self.assertEqual(seen, ["1", "2"])
        self.assertEqual(r.journal_entries, 2)

    def test_corrupt_or_idless_journal_fails(self):
        write_snapshot(self.snaps, "001", {})
        for content in ("{", "[]", json.dumps({"x": 1})):
            (self.journal / "a.json").write_text(content)
            self.assertFalse(self.engine().run().success, content)

    def test_apply_error_fails(self):
        write_snapshot(self.snaps, "001", {})
        (self.journal / "a.json").write_text(json.dumps({"tx_id": "1"}))

        def boom(tx):
            raise RuntimeError

        self.assertFalse(self.engine(apply=boom).run().success)

    def test_unhealthy_fails(self):
        write_snapshot(self.snaps, "001", {})
        for score in (10.0, float("nan")):
            r = self.engine(health_check=lambda s=score: s).run()
            self.assertFalse(r.success)
            self.assertEqual(r.state, "FAILED")
        self.assertTrue(self.engine(health_check=lambda: 95).run().success)


if __name__ == "__main__":
    unittest.main()
