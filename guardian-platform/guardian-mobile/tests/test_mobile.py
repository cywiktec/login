import json
import os
import tempfile
import unittest

from guardian_mobile.alerts import AlertInbox
from guardian_mobile.app import FakeTransport, GuardianApp
from guardian_mobile.maps import MapView
from guardian_mobile.missions import DraftError, MissionDraft, MissionLibrary
from guardian_mobile.settings import Settings, SettingsError
from guardian_mobile.telemetry import TelemetryView, parse_telemetry


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


class SettingsTests(unittest.TestCase):
    def test_validation(self):
        s = Settings()
        for key, bad in [("base_url", "http://x"), ("language", "de"), ("stale_after_s", 0),
                         ("stale_after_s", True), ("confirm_commands", "yes")]:
            with self.assertRaises(SettingsError):
                s.set(key, bad)
        with self.assertRaises(SettingsError):
            s.set("nope", 1)
        s.set("base_url", "https://robot.local")
        self.assertEqual(s.get("base_url"), "https://robot.local")

    def test_persistence_and_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.json")
            Settings(path).set("language", "en")
            self.assertEqual(Settings(path).get("language"), "en")
            with open(path, "w") as f:
                f.write("{broken")
            self.assertEqual(Settings(path).get("language"), "pl")
            with open(path, "w") as f:
                json.dump({"language": "xx", "units": "imperial", "evil": 1}, f)
            s = Settings(path)
            self.assertEqual((s.get("language"), s.get("units")), ("pl", "imperial"))
            self.assertEqual(os.listdir(d), ["s.json"])


class TelemetryTests(unittest.TestCase):
    def test_parse_rejects_bad(self):
        for bad in (None, {}, {"state": "FLYING"}, {"state": "READY", "battery_pct": 120},
                    {"state": "READY", "battery_pct": float("nan")}, {"state": "READY", "x": "1"}):
            self.assertIsNone(parse_telemetry(bad, 0), bad)
        self.assertEqual(parse_telemetry({"state": "READY", "battery_pct": 50}, 1).battery_pct, 50.0)

    def test_staleness(self):
        clock = Clock()
        view = TelemetryView(stale_after=5, clock=clock)
        self.assertEqual(view.status(), "no_data")
        self.assertTrue(view.update({"state": "READY"}))
        self.assertEqual(view.status(), "live")
        clock.t += 6
        self.assertEqual(view.status(), "stale")
        self.assertFalse(view.update({"state": "bogus"}))
        self.assertEqual(view.status(), "stale")


class AlertTests(unittest.TestCase):
    def test_dedupe_order_ack(self):
        clock = Clock()
        inbox = AlertInbox(clock=clock)
        inbox.add("bat", "warning", "low")
        clock.t += 1
        inbox.add("fence", "critical", "outside")
        inbox.add("bat", "warning", "low again")
        self.assertEqual([a.key for a in inbox.active()], ["fence", "bat"])
        self.assertEqual(inbox.active()[1].count, 2)
        self.assertTrue(inbox.has_critical())
        inbox.acknowledge("fence")
        self.assertFalse(inbox.has_critical())
        inbox.add("fence", "info", "again")
        self.assertEqual(inbox.active()[0].key, "fence")  # unacked again, severity kept

    def test_unknown_severity_is_critical(self):
        inbox = AlertInbox()
        self.assertEqual(inbox.add("x", "weird", "m").severity, "critical")

    def test_trim_keeps_critical(self):
        inbox = AlertInbox(max_alerts=2)
        inbox.add("c", "critical", "m")
        inbox.add("i", "info", "m")
        inbox.add("w", "warning", "m")
        self.assertEqual({a.key for a in inbox.active()}, {"c", "w"})


class MapTests(unittest.TestCase):
    def test_conversion_roundtrip(self):
        view = MapView(0, 0, 10, 20, 100, 200)
        self.assertEqual(view.to_screen(0, 0), (0, 200))
        self.assertEqual(view.to_screen(10, 20), (100, 0))
        wx, wy = view.to_world(*view.to_screen(3, 4))
        self.assertAlmostEqual(wx, 3)
        self.assertAlmostEqual(wy, 4)

    def test_invalid_view(self):
        with self.assertRaises(ValueError):
            MapView(0, 0, 0, 1, 10, 10)
        with self.assertRaises(ValueError):
            MapView(0, 0, 1, 1, 0, 10)

    def test_geofence(self):
        view = MapView(0, 0, 10, 10, 100, 100)
        with self.assertRaises(ValueError):
            view.set_geofence([(0, 0), (1, 1)])
        view.set_geofence([(0, 0), (5, 0), (5, 5), (0, 5)])
        self.assertTrue(view.inside_geofence(2, 2))
        self.assertFalse(view.inside_geofence(7, 2))
        self.assertFalse(view.contains(float("nan"), 1))


class MissionTests(unittest.TestCase):
    def test_draft_validation(self):
        view = MapView(0, 0, 10, 10, 100, 100)
        view.set_geofence([(0, 0), (5, 0), (5, 5), (0, 5)])
        draft = MissionDraft("Patrol")
        draft.add_waypoint(1, 1, view)
        for x, y in [(7, 1), (20, 20), (float("inf"), 1), ("1", 1)]:
            with self.assertRaises(DraftError):
                draft.add_waypoint(x, y, view)
        self.assertEqual(draft.to_payload()["waypoints"], [[1.0, 1.0]])

    def test_invalid_drafts(self):
        with self.assertRaises(DraftError):
            MissionDraft("x").validate()
        d = MissionDraft(" ", [(1.0, 1.0)])
        with self.assertRaises(DraftError):
            d.validate()
        d = MissionDraft("a", [(1.0, 1.0)], loops=0)
        with self.assertRaises(DraftError):
            d.validate()
        with self.assertRaises(DraftError):
            d.remove_waypoint(5)

    def test_limit_and_library(self):
        d = MissionDraft("a")
        for i in range(50):
            d.add_waypoint(i, 0)
        with self.assertRaises(DraftError):
            d.add_waypoint(1, 1)
        lib = MissionLibrary()
        lib.save(d)
        self.assertEqual(lib.names(), ["a"])
        with self.assertRaises(DraftError):
            lib.save(MissionDraft("empty"))
        self.assertTrue(lib.delete("a"))


class AppTests(unittest.TestCase):
    def test_actuating_needs_confirmation(self):
        t = FakeTransport()
        app = GuardianApp(t)
        self.assertEqual(app.send_command("MISIEK, rozpocznij patrol.").status, "needs_confirmation")
        self.assertEqual(t.sent, [])
        self.assertEqual(app.confirm_pending().status, "sent")
        self.assertEqual(t.sent[0][1], {"text": "MISIEK, rozpocznij patrol."})
        self.assertEqual(app.confirm_pending().status, "rejected")

    def test_cancel(self):
        app = GuardianApp(FakeTransport())
        app.send_command("MISIEK, wróć do bazy.")
        app.cancel_pending()
        self.assertEqual(app.confirm_pending().status, "rejected")

    def test_readonly_and_confirmation_off(self):
        t = FakeTransport()
        app = GuardianApp(t)
        self.assertEqual(app.send_command("MISIEK, raport stanu.").status, "sent")
        app.settings.set("confirm_commands", False)
        self.assertEqual(app.send_command("MISIEK, wróć do bazy.").status, "sent")

    def test_emergency_stop_immediate_even_when_offline_data(self):
        t = FakeTransport()
        app = GuardianApp(t)
        self.assertEqual(app.emergency_stop().status, "sent")
        self.assertEqual(t.sent[-1][1], {"text": "MISIEK, stop"})
        self.assertEqual(GuardianApp(FakeTransport(fail=True)).emergency_stop().status, "offline")

    def test_robot_rejection_and_bad_reply(self):
        app = GuardianApp(FakeTransport({"/command": {"ok": False, "error": "denied in MISSION"}}))
        out = app.send_command("MISIEK, raport stanu")
        self.assertEqual((out.status, out.detail), ("rejected", "denied in MISSION"))
        app = GuardianApp(FakeTransport({"/command": "garbage"}))
        self.assertEqual(app.send_command("MISIEK, raport stanu").status, "rejected")

    def test_submit_mission(self):
        t = FakeTransport()
        app = GuardianApp(t)
        self.assertEqual(app.submit_mission(MissionDraft("empty")).status, "rejected")
        draft = MissionDraft("p", [(1.0, 2.0)])
        self.assertEqual(app.submit_mission(draft).status, "sent")
        self.assertEqual(t.sent[-1][0], "/missions")

    def test_refresh(self):
        app = GuardianApp(FakeTransport({"/telemetry": {"state": "READY", "battery_pct": 80}}))
        self.assertTrue(app.refresh())
        self.assertEqual(app.telemetry.latest.state, "READY")
        self.assertFalse(GuardianApp(FakeTransport(fail=True)).refresh())


if __name__ == "__main__":
    unittest.main()
