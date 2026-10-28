import json
import os
import tempfile
import unittest

from guardian_backup.hash import sha256_bytes, sha256_file, sha256_obj, verify
from guardian_backup.journaling import Journal
from guardian_backup.recovery import plan_auto_resume, recover_state
from guardian_backup.retention import apply_retention
from guardian_backup.rollback import restore_rolled_back, rollback_to
from guardian_backup.snapshot import CorruptSnapshot, SnapshotStore, write_atomic


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        self.addCleanup(self._tmp.cleanup)


class HashTests(Base):
    def test_known_vector(self):
        self.assertEqual(sha256_bytes(b"abc"),
                         "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_file_and_object(self):
        path = os.path.join(self.dir, "f")
        with open(path, "wb") as f:
            f.write(b"abc")
        self.assertEqual(sha256_file(path), sha256_bytes(b"abc"))
        self.assertEqual(sha256_obj({"b": 1, "a": 2}), sha256_obj({"a": 2, "b": 1}))
        self.assertTrue(verify("aa", "aa"))
        self.assertFalse(verify("aa", "ab"))
        self.assertFalse(verify(None, "ab"))


class SnapshotTests(Base):
    def test_roundtrip_and_latest(self):
        store = SnapshotStore(self.dir)
        store.save({"state": "READY"}, 1)
        store.save({"state": "MISSION"}, 2)
        self.assertEqual(store.load(1)["state"], {"state": "READY"})
        self.assertEqual(store.latest_valid()["seq"], 2)

    def test_atomic_write_leaves_no_temp_files(self):
        store = SnapshotStore(self.dir)
        store.save({"a": 1}, 1)
        self.assertEqual(os.listdir(self.dir), ["snapshot-0000000001.json"])

    def test_failed_write_keeps_old_file(self):
        path = os.path.join(self.dir, "x")
        write_atomic(path, b"old")
        with self.assertRaises(TypeError):
            write_atomic(path, "not bytes")
        with open(path, "rb") as f:
            self.assertEqual(f.read(), b"old")
        self.assertEqual(os.listdir(self.dir), ["x"])

    def test_tampering_detected_and_skipped(self):
        store = SnapshotStore(self.dir)
        store.save({"v": 1}, 1)
        path = store.save({"v": 2}, 2)
        with open(path) as f:
            envelope = json.load(f)
        envelope["state"]["v"] = 999
        with open(path, "w") as f:
            json.dump(envelope, f)
        with self.assertRaises(CorruptSnapshot):
            store.load(2)
        self.assertEqual(store.latest_valid()["seq"], 1)

    def test_garbage_and_missing(self):
        store = SnapshotStore(self.dir)
        with open(store.path_for(3), "w") as f:
            f.write("{not json")
        with self.assertRaises(CorruptSnapshot):
            store.load(3)
        with self.assertRaises(CorruptSnapshot):
            store.load(99)
        self.assertIsNone(store.latest_valid())

    def test_invalid_seq_and_nan(self):
        store = SnapshotStore(self.dir)
        for bad in (-1, True, "1"):
            with self.assertRaises(ValueError):
                store.save({}, bad)
        with self.assertRaises(ValueError):
            store.save({"x": float("nan")}, 1)
        self.assertEqual(store.list_seqs(), [])


class JournalTests(Base):
    def test_append_and_reopen(self):
        path = os.path.join(self.dir, "j.log")
        j = Journal(path)
        self.assertEqual([j.append({"n": i}) for i in range(3)], [1, 2, 3])
        j.close()
        j2 = Journal(path)
        self.assertEqual(j2.last_seq, 3)
        self.assertEqual(j2.append({"n": 3}), 4)
        self.assertEqual([e["data"]["n"] for e in j2.entries(after_seq=2)], [2, 3])
        self.assertFalse(j2.damaged)

    def test_torn_tail_is_dropped(self):
        path = os.path.join(self.dir, "j.log")
        j = Journal(path)
        j.append({"n": 1})
        j.append({"n": 2})
        j.close()
        with open(path, "ab") as f:
            f.write(b'{"seq": 3, "ts": 1, "da')
        j2 = Journal(path)
        self.assertTrue(j2.damaged)
        self.assertEqual(j2.last_seq, 2)
        j2.append({"n": 3})
        self.assertEqual(len(j2.entries()), 3)
        j2.close()
        j3 = Journal(path)
        self.addCleanup(j3.close)
        self.assertFalse(j3.damaged)

    def test_tampered_entry_cuts_chain(self):
        path = os.path.join(self.dir, "j.log")
        j = Journal(path)
        for i in range(3):
            j.append({"n": i})
        j.close()
        with open(path) as f:
            lines = f.readlines()
        lines[1] = lines[1].replace('"n": 1', '"n": 9').replace('"n":1', '"n":9')
        with open(path, "w") as f:
            f.writelines(lines)
        j2 = Journal(path)
        self.assertTrue(j2.damaged)
        self.assertEqual(j2.last_seq, 1)


class RollbackRetentionTests(Base):
    def test_rollback_is_reversible(self):
        store = SnapshotStore(self.dir)
        for i in range(1, 4):
            store.save({"v": i}, i)
        self.assertEqual(rollback_to(store, 1), [2, 3])
        self.assertEqual(store.list_seqs(), [1])
        self.assertEqual(len(restore_rolled_back(store)), 2)
        self.assertEqual(store.list_seqs(), [1, 2, 3])

    def test_rollback_to_corrupt_target_moves_nothing(self):
        store = SnapshotStore(self.dir)
        store.save({"v": 1}, 1)
        store.save({"v": 2}, 2)
        with open(store.path_for(1), "w") as f:
            f.write("junk")
        with self.assertRaises(CorruptSnapshot):
            rollback_to(store, 1)
        self.assertEqual(store.list_seqs(), [1, 2])

    def test_retention_keeps_last_and_latest_valid(self):
        store = SnapshotStore(self.dir)
        for i in range(1, 6):
            store.save({"v": i}, i)
        with open(store.path_for(5), "w") as f:
            f.write("junk")
        self.assertEqual(apply_retention(store, keep_last=2), [1, 2, 3])
        self.assertEqual(store.list_seqs(), [4, 5])  # 5 is corrupt but inside keep_last; 4 is the newest valid

    def test_retention_age_and_foreign_files(self):
        store = SnapshotStore(self.dir)
        for i in range(1, 4):
            store.save({"v": i}, i)
        other = os.path.join(self.dir, "notes.txt")
        open(other, "w").close()
        self.assertEqual(apply_retention(store, keep_last=1, max_age_s=3600), [])
        self.assertEqual(apply_retention(store, keep_last=1, max_age_s=0, now=1e12), [1, 2])
        self.assertTrue(os.path.exists(other))
        with self.assertRaises(ValueError):
            apply_retention(store, keep_last=0)


class RecoveryTests(Base):
    @staticmethod
    def apply(state, data):
        return {**state, **data}

    def make(self):
        store = SnapshotStore(self.dir)
        journal = Journal(os.path.join(self.dir, "j.log"))
        self.addCleanup(journal.close)
        return store, journal

    def test_replay_after_snapshot(self):
        store, journal = self.make()
        journal.append({"a": 1})
        store.save({"a": 1}, journal.last_seq)
        journal.append({"b": 2})
        journal.append({"c": 3})
        rec = recover_state(store, journal, self.apply)
        self.assertEqual((rec.state, rec.replayed, rec.last_seq), ({"a": 1, "b": 2, "c": 3}, 2, 3))

    def test_no_snapshot(self):
        store, journal = self.make()
        self.assertIsNone(recover_state(store, journal, self.apply))

    def resume(self, state, **kwargs):
        store, journal = self.make()
        store.save(state, 1)
        rec = recover_state(store, journal, self.apply)
        return plan_auto_resume(rec, **kwargs)

    def test_auto_resume_happy_path(self):
        plan = self.resume({"state": "MISSION", "checkpoint": {"wp": 3}}, saved_at=100, now=110)
        self.assertEqual((plan.action, plan.checkpoint), ("resume", {"wp": 3}))

    def test_auto_resume_fails_closed(self):
        mission = {"state": "MISSION", "checkpoint": {"wp": 3}}
        self.assertEqual(self.resume({"state": "READY"}, saved_at=100, now=110).action, "none")
        self.assertEqual(self.resume(mission, saved_at=100, now=110, enabled=False).action, "manual")
        self.assertEqual(self.resume(mission, saved_at=100, now=1000).action, "manual")
        self.assertEqual(self.resume(mission, saved_at=None, now=1000).action, "manual")
        self.assertEqual(self.resume({"state": "MISSION"}, saved_at=100, now=110).action, "manual")
        self.assertEqual(plan_auto_resume(None, 0).action, "manual")

    def test_damaged_journal_blocks_resume(self):
        store, journal = self.make()
        journal.append({"a": 1})
        journal.close()
        with open(journal.path, "ab") as f:
            f.write(b"garbage")
        journal = Journal(journal.path)
        self.addCleanup(journal.close)
        store.save({"state": "MISSION", "checkpoint": {"wp": 1}}, 1)
        rec = recover_state(store, journal, self.apply)
        self.assertEqual(plan_auto_resume(rec, 100, now=101).action, "manual")


if __name__ == "__main__":
    unittest.main()
