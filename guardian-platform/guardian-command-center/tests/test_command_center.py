import unittest

from guardian_command_center import analytics, tactical_map
from guardian_command_center.fleet_manager import CommandRefused, FleetManager
from guardian_command_center.incident_manager import IncidentManager
from guardian_command_center.mission_overview import MissionOverview

SQUARE = [(0, 0), (10, 0), (10, 10), (0, 10)]


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class FleetTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.fleet = FleetManager(stale_after=10, clock=self.clock)
        self.fleet.heartbeat("r1", "READY", 80, (1, 1))

    def test_status_progression(self):
        self.assertEqual(self.fleet.status("r1"), "online")
        self.clock.t = 11
        self.assertEqual(self.fleet.status("r1"), "stale")
        self.assertEqual(self.fleet.status("nope"), "unknown")

    def test_heartbeat_validation(self):
        for kwargs in ({"battery_pct": 101}, {"battery_pct": float("nan")}, {"position": (float("inf"), 0)}):
            with self.assertRaises(ValueError):
                self.fleet.heartbeat("r1", "READY", **kwargs)
        with self.assertRaises(ValueError):
            self.fleet.heartbeat("", "READY")

    def test_role_checks(self):
        with self.assertRaises(CommandRefused):
            self.fleet.issue("r1", "start_patrol", "ola", "viewer")
        with self.assertRaises(CommandRefused):
            self.fleet.issue("r1", "start_patrol", "ola", "hacker")
        with self.assertRaises(CommandRefused):
            self.fleet.issue("r1", "self_destruct", "ola", "admin")
        with self.assertRaises(CommandRefused):
            self.fleet.issue("zz", "start_patrol", "ola", "admin")
        with self.assertRaises(CommandRefused):
            self.fleet.issue("r1", "start_patrol", "", "admin")
        self.fleet.issue("r1", "start_patrol", "ola", "operator")

    def test_estop_open_to_viewer_front_of_queue_and_works_when_stale(self):
        self.fleet.issue("r1", "start_patrol", "ola", "operator")
        self.clock.t = 100
        with self.assertRaises(CommandRefused):
            self.fleet.issue("r1", "return_to_base", "ola", "operator")
        self.fleet.issue("r1", "emergency_stop", "ola", "viewer")
        self.assertEqual(self.fleet.next_command("r1")["command"], "emergency_stop")
        self.assertEqual(self.fleet.next_command("r1")["command"], "start_patrol")
        self.assertIsNone(self.fleet.next_command("r1"))

    def test_estop_all(self):
        self.fleet.heartbeat("r2", "MISSION")
        self.clock.t = 100
        self.assertEqual(self.fleet.estop_all("ola", "viewer"), ["r1", "r2"])


class IncidentTests(unittest.TestCase):
    def test_lifecycle_and_dedupe(self):
        m = IncidentManager()
        a = m.open("r1", "low_battery", 3, 0)
        self.assertEqual(m.open("r1", "low_battery", 1, 5), a)
        self.assertEqual(m.get(a)["severity"], 1)
        self.assertEqual(m.get(a)["count"], 2)
        with self.assertRaises(ValueError):
            m.resolve(a, "ola", 6, "x")
        m.ack(a, "ola", 10)
        with self.assertRaises(ValueError):
            m.ack(a, "ola", 11)
        with self.assertRaises(ValueError):
            m.resolve(a, "ola", 12, "")
        m.resolve(a, "ola", 12, "charged")
        self.assertNotEqual(m.open("r1", "low_battery", 3, 20), a)

    def test_validation(self):
        m = IncidentManager()
        for sev in (0, 5, "1", None):
            with self.assertRaises(ValueError):
                m.open("r1", "k", sev, 0)

    def test_overdue_sorted(self):
        m = IncidentManager()
        m.open("r1", "a", 4, 0)
        m.open("r2", "b", 1, 0)
        acked = m.open("r3", "c", 1, 0)
        m.ack(acked, "ola", 1)
        self.assertEqual([i["kind"] for i in m.overdue(100)], ["b"])
        self.assertEqual([i["kind"] for i in m.overdue(4000)], ["b", "a"])


class TacticalMapTests(unittest.TestCase):
    def test_flags(self):
        clock = Clock()
        f = FleetManager(clock=clock)
        f.heartbeat("in", "READY", position=(5, 5))
        f.heartbeat("out", "READY", position=(50, 5))
        f.heartbeat("nopos", "READY")
        f.heartbeat("old", "READY", position=(1, 1))
        clock.t = 5
        for r in ("in", "out", "nopos"):
            f.heartbeat(r, "READY", position=f.robots()[r]["position"])
        clock.t = 12
        for r in ("in", "out", "nopos"):
            f.heartbeat(r, "READY", position=f.robots()[r]["position"])
        coll = tactical_map.build(f.robots(), SQUARE)
        self.assertEqual(tactical_map.alerts(coll), ["old", "out"])
        nopos = [x for x in coll["features"] if x["properties"].get("id") == "nopos"][0]
        self.assertIsNone(nopos["geometry"])
        self.assertIsNone(nopos["properties"]["inside_geofence"])
        with self.assertRaises(ValueError):
            tactical_map.build({}, [(0, 0)])


class MissionTests(unittest.TestCase):
    def test_flow_and_rules(self):
        o = MissionOverview(max_active_s=100)
        o.create("m1", "r1", 0)
        o.create("m2", "r1", 0)
        with self.assertRaises(ValueError):
            o.create("m1", "r1", 0)
        with self.assertRaises(ValueError):
            o.move("m1", "done", 1)
        o.move("m1", "active", 1)
        with self.assertRaises(ValueError):
            o.move("m2", "active", 2)  # one active mission per robot
        self.assertEqual(o.stuck(50), [])
        self.assertEqual(o.stuck(200), ["m1"])
        o.move("m1", "done", 60)
        with self.assertRaises(ValueError):
            o.move("m1", "aborted", 61)
        o.move("m2", "aborted", 62)
        self.assertEqual(o.counts(), {"pending": 0, "active": 0, "done": 1, "aborted": 1})
        self.assertEqual(len(o.by_robot("r1")), 2)


class AnalyticsTests(unittest.TestCase):
    def test_empty_is_none(self):
        self.assertIsNone(analytics.mean_time_to_ack([]))
        self.assertIsNone(analytics.mission_success_rate([{"state": "active"}]))
        self.assertIsNone(analytics.availability([]))

    def test_values(self):
        inc = [{"opened": 0, "acked": 10, "severity": 2, "status": "resolved"},
               {"opened": 0, "acked": 30, "severity": 2, "status": "acknowledged"},
               {"opened": 0, "acked": None, "severity": 1, "status": "open"}]
        self.assertEqual(analytics.mean_time_to_ack(inc), 20)
        self.assertEqual(analytics.incidents_by_severity(inc), {1: 1, 2: 2})
        self.assertEqual(analytics.unresolved(inc), 2)
        self.assertEqual(analytics.mission_success_rate([{"state": "done"}, {"state": "aborted"}]), 0.5)
        self.assertEqual(analytics.availability([{"a": "online", "b": "stale"}]), 0.5)


if __name__ == "__main__":
    unittest.main()
