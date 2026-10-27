import tempfile
import unittest

from guardian_mission_manager.checkpoint_manager import Checkpoint, CheckpointManager
from guardian_mission_manager.mission_fsm import (
    InvalidMissionTransition,
    MissionFSM,
    MissionState,
)
from guardian_mission_manager.planner import Planner
from guardian_mission_manager.recovery import RecoveryManager
from guardian_mission_manager.route_manager import Route, RouteManager, Waypoint
from guardian_mission_manager.scheduler import Scheduler


def sample_route(route_id="r1"):
    return Route(route_id, [Waypoint("a", 0, 0), Waypoint("b", 3, 4), Waypoint("c", 3, 10)])


class RouteTests(unittest.TestCase):
    def test_length_and_reverse(self):
        route = sample_route()
        self.assertAlmostEqual(route.length(), 11.0)
        self.assertEqual([w.name for w in route.reversed().waypoints], ["c", "b", "a"])

    def test_validation(self):
        with self.assertRaises(ValueError):
            Route("x", [])
        with self.assertRaises(ValueError):
            Route("x", [Waypoint("a", 0, 0), Waypoint("a", 1, 1)])

    def test_manager(self):
        manager = RouteManager()
        manager.add(sample_route("r1"))
        self.assertEqual(manager.ids(), ["r1"])
        with self.assertRaises(ValueError):
            manager.add(sample_route("r1"))
        with self.assertRaises(KeyError):
            manager.get("missing")


class PlannerTests(unittest.TestCase):
    def test_steps_with_loops_and_base(self):
        plan = Planner().patrol("m1", sample_route(), loops=2)
        self.assertEqual(plan.steps(), ["a", "b", "c", "a", "b", "c", "base"])

    def test_no_return_to_base(self):
        plan = Planner().patrol("m1", sample_route(), return_to_base=False)
        self.assertEqual(plan.steps(), ["a", "b", "c"])

    def test_invalid_loops(self):
        with self.assertRaises(ValueError):
            Planner().patrol("m1", sample_route(), loops=0)


class SchedulerTests(unittest.TestCase):
    def test_due_ordering_and_cancel(self):
        now = [100]
        scheduler = Scheduler(clock=lambda: now[0])
        scheduler.schedule("late", 200)
        scheduler.schedule("low", 50, priority=5)
        scheduler.schedule("high", 90, priority=1)
        scheduler.schedule("gone", 60)
        scheduler.cancel("gone")
        self.assertEqual(scheduler.pop_due(), ["high", "low"])
        self.assertEqual(scheduler.pending(), 1)
        now[0] = 200
        self.assertEqual(scheduler.pop_due(), ["late"])

    def test_nothing_due(self):
        scheduler = Scheduler(clock=lambda: 0)
        scheduler.schedule("m", 10)
        self.assertEqual(scheduler.pop_due(), [])


class MissionFSMTests(unittest.TestCase):
    def test_happy_path(self):
        fsm = MissionFSM()
        for state in (MissionState.RUNNING, MissionState.PAUSED,
                      MissionState.RUNNING, MissionState.COMPLETED):
            fsm.transition(state)
        self.assertTrue(fsm.finished)

    def test_invalid_and_terminal(self):
        fsm = MissionFSM()
        with self.assertRaises(InvalidMissionTransition):
            fsm.transition(MissionState.COMPLETED)
        fsm.transition(MissionState.ABORTED)
        with self.assertRaises(InvalidMissionTransition):
            fsm.transition(MissionState.RUNNING)


class CheckpointTests(unittest.TestCase):
    def test_roundtrip_missing_and_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = CheckpointManager(directory)
            self.assertIsNone(manager.load("m1"))
            checkpoint = Checkpoint("m1", "RUNNING", 1, ["a", "b", "c"])
            manager.save(checkpoint)
            self.assertEqual(manager.load("m1"), checkpoint)
            self.assertEqual(manager.list_ids(), ["m1"])
            manager.delete("m1")
            self.assertIsNone(manager.load("m1"))

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = CheckpointManager(directory)
            for bad in ("../evil", "a/b", "", ".."):
                with self.assertRaises(ValueError):
                    manager.save(Checkpoint(bad, "RUNNING", 0, []))


class RecoveryTests(unittest.TestCase):
    def test_interrupted_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoints = CheckpointManager(directory)
            checkpoints.save(Checkpoint("run", "RUNNING", 1, ["a", "b", "c"]))
            checkpoints.save(Checkpoint("done", "COMPLETED", 3, ["a", "b", "c"]))
            recovery = RecoveryManager(checkpoints)

            self.assertEqual(recovery.interrupted(), ["run"])
            checkpoint, remaining = recovery.resume("run")
            self.assertEqual(remaining, ["b", "c"])
            with self.assertRaises(ValueError):
                recovery.resume("done")
            with self.assertRaises(LookupError):
                recovery.resume("nope")

            recovery.mark_failed("run")
            self.assertEqual(recovery.interrupted(), [])
