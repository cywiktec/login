import unittest

from guardian_web.dashboard import build_dashboard
from guardian_web.fleet import EMERGENCY, OFFLINE, ONLINE, STALE, FleetRegistry
from guardian_web.maps import MapError, MapStore, validate_map
from guardian_web.reports import mission_report, to_csv, to_html, to_markdown
from guardian_web.settings import PermissionDenied, SettingsError, WebSettings


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class FleetTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.fleet = FleetRegistry(stale_after=10, offline_after=60, clock=self.clock)

    def test_status_ageing(self):
        self.assertTrue(self.fleet.heartbeat("go2-01", "READY", 80))
        self.assertEqual(self.fleet.status("go2-01"), ONLINE)
        self.clock.t += 11
        self.assertEqual(self.fleet.status("go2-01"), STALE)
        self.clock.t += 60
        self.assertEqual(self.fleet.status("go2-01"), OFFLINE)
        self.assertEqual(self.fleet.status("unknown"), OFFLINE)

    def test_emergency_visible_even_when_stale_but_not_offline(self):
        self.fleet.heartbeat("a", "EMERGENCY_STOP")
        self.clock.t += 30
        self.assertEqual(self.fleet.status("a"), EMERGENCY)
        self.clock.t += 40
        self.assertEqual(self.fleet.status("a"), OFFLINE)

    def test_invalid_heartbeats(self):
        for args in (("BAD", "READY"), ("a", 5), ("a", "READY", 101), ("a", "READY", float("nan")),
                     ("a", "READY", True), (None, "READY")):
            self.assertFalse(self.fleet.heartbeat(*args), args)
        self.assertEqual(self.fleet.robots(), [])

    def test_ordering_and_summary(self):
        self.fleet.heartbeat("c", "READY")
        self.fleet.heartbeat("b", "EMERGENCY_STOP")
        self.fleet.heartbeat("a", "READY")
        self.assertEqual([r.robot_id for r, _ in self.fleet.robots()], ["b", "a", "c"])
        self.assertEqual(self.fleet.summary()[EMERGENCY], 1)
        self.assertTrue(self.fleet.remove("a"))
        self.assertFalse(self.fleet.remove("a"))

    def test_config_validation(self):
        with self.assertRaises(ValueError):
            FleetRegistry(stale_after=60, offline_after=10)


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.fleet = FleetRegistry(clock=self.clock)

    def test_empty_fleet_is_unknown_not_ok(self):
        self.assertEqual(build_dashboard(self.fleet)["overall"], "unknown")

    def test_overall_levels(self):
        self.fleet.heartbeat("a", "READY", 90)
        self.assertEqual(build_dashboard(self.fleet)["overall"], "ok")
        self.assertEqual(build_dashboard(self.fleet, [{"severity": "info", "message": "x"}])["overall"], "warning")
        self.assertEqual(build_dashboard(self.fleet, [{"severity": "critical", "message": "x"}])["overall"], "critical")
        self.fleet.heartbeat("b", "EMERGENCY_STOP")
        self.assertEqual(build_dashboard(self.fleet)["overall"], "emergency")

    def test_stale_and_offline(self):
        self.fleet.heartbeat("a", "READY")
        self.clock.t += 20
        self.assertEqual(build_dashboard(self.fleet)["overall"], "warning")
        self.clock.t += 60
        self.assertEqual(build_dashboard(self.fleet)["overall"], "critical")

    def test_alert_cleaning_and_order(self):
        self.fleet.heartbeat("a", "READY")
        data = build_dashboard(self.fleet, [{"severity": "info", "message": "i"}, "junk",
                                            {"severity": "weird", "message": "w"}])
        self.assertEqual([a["severity"] for a in data["alerts"]], ["critical", "info"])


class ReportTests(unittest.TestCase):
    EVENTS = [{"ts": 20, "kind": "wp", "message": "b"}, {"ts": 10, "kind": "start", "message": "a|b"},
              {"ts": "x", "kind": "bad"}, "junk", {"ts": True, "kind": "bad"}]

    def test_report(self):
        r = mission_report("m1", self.EVENTS)
        self.assertEqual([e["ts"] for e in r["events"]], [10.0, 20.0])
        self.assertEqual((r["invalid_events"], r["duration_s"]), (3, 10.0))
        self.assertEqual(r["counts"], {"start": 1, "wp": 1})
        self.assertEqual(mission_report("m", [])["duration_s"], 0.0)

    def test_html_is_escaped(self):
        r = mission_report("<script>", [{"ts": 1, "kind": "<b>", "message": "<img onerror=x>"}])
        out = to_html(r)
        self.assertNotIn("<script>", out)
        self.assertNotIn("<img", out)
        self.assertIn("&lt;img onerror=x&gt;", out)

    def test_markdown_table_cells(self):
        out = to_markdown(mission_report("m", self.EVENTS))
        self.assertIn("a\\|b", out)

    def test_csv_formula_injection(self):
        r = mission_report("m", [{"ts": 1, "kind": "k", "message": "=HYPERLINK(\"x\")"},
                                 {"ts": 2, "kind": "k", "message": "ok, with comma"}])
        out = to_csv(r)
        self.assertIn("'=HYPERLINK", out)
        self.assertIn('"ok, with comma"', out)


class MapTests(unittest.TestCase):
    GOOD = {"bounds": [0, 0, 10, 10], "geofence": [[1, 1], [9, 1], [9, 9], [1, 9]], "waypoints": [[2, 2]]}

    def test_valid(self):
        store = MapStore()
        self.assertEqual(store.save("Hall 1", self.GOOD), 1)
        self.assertEqual(store.save("Hall 1", self.GOOD), 2)
        self.assertEqual(store.get("Hall 1", 1)["bounds"], [0.0, 0.0, 10.0, 10.0])
        self.assertIsNone(store.get("Hall 1", 3))
        self.assertIsNone(store.get("nope"))
        self.assertEqual((store.names(), store.version_count("Hall 1")), (["Hall 1"], 2))

    def test_invalid(self):
        bad = [
            {**self.GOOD, "bounds": [0, 0, 0, 10]},
            {**self.GOOD, "bounds": [0, 0, 10]},
            {**self.GOOD, "geofence": [[1, 1], [2, 2]]},
            {**self.GOOD, "geofence": [[1, 1], [2, 2], [3, 3]]},  # zero area
            {**self.GOOD, "geofence": [[1, 1], [9, 1], [20, 9]]},
            {**self.GOOD, "waypoints": [[11, 2]]},
            {**self.GOOD, "waypoints": [[float("nan"), 2]]},
            {**self.GOOD, "waypoints": [["1", 2]]},
            {"bounds": [0, 0, 10, 10]},
            "x",
        ]
        for d in bad:
            with self.assertRaises(MapError, msg=d):
                validate_map(d)

    def test_names(self):
        for name in ("", "../x", "a/b", None, "x" * 100):
            with self.assertRaises(MapError):
                MapStore().save(name, self.GOOD)


class SettingsTests(unittest.TestCase):
    def test_roles(self):
        s = WebSettings()
        s.set("theme", "dark", "operator")
        with self.assertRaises(PermissionDenied):
            s.set("theme", "light", "viewer")
        with self.assertRaises(PermissionDenied):
            s.set("require_command_confirmation", False, "operator")
        s.set("require_command_confirmation", False, "admin")
        with self.assertRaises(PermissionDenied):
            s.set("theme", "dark", "root")
        self.assertEqual(s.get("theme"), "dark")

    def test_validation(self):
        s = WebSettings()
        for key, bad in (("refresh_s", 0), ("refresh_s", True), ("theme", "blue"),
                         ("session_timeout_min", 1000)):
            with self.assertRaises(SettingsError):
                s.set(key, bad, "admin")
        with self.assertRaises(SettingsError):
            s.set("nope", 1, "admin")
        with self.assertRaises(SettingsError):
            s.get("nope")
        self.assertEqual(s.get("refresh_s"), 5)


if __name__ == "__main__":
    unittest.main()
