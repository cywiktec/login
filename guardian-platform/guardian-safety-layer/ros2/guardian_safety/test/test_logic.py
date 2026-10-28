import unittest

from guardian_safety.logic import (EmergencyStopLogic, GeofenceLogic, SafetyManagerLogic,
                                   WatchdogLogic, parse_polygon, require_positive)
from guardian_safety_layer.safety_fsm import SafetyLevel

SQUARE = [(0, 0), (10, 0), (10, 10), (0, 10)]


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def healthy(m, battery=80.0):
    m.update_input("estop", False)
    m.update_input("watchdog", True)
    m.update_input("geofence", True)
    m.update_battery(battery)


class Helpers(unittest.TestCase):
    def test_polygon(self):
        self.assertEqual(parse_polygon([0, 0, 1, 0, 1, 1]), [(0, 0), (1, 0), (1, 1)])
        for bad in (None, [0, 0, 1, 1], [0, 0, 1, 0, 1], [0, 0, 1, 0, 1, float("nan")]):
            with self.assertRaises(ValueError):
                parse_polygon(bad)

    def test_positive(self):
        for bad in (0, -1, float("nan"), None, True):
            with self.assertRaises(ValueError):
                require_positive(bad, "x")


class Watchdog(unittest.TestCase):
    def test_flow(self):
        c = Clock()
        w = WatchdogLogic(["a"], 1.0, c)
        self.assertTrue(w.ok())
        c.t += 1.5
        self.assertEqual(w.expired(), ["a"])
        w.beat("a")
        self.assertTrue(w.ok())

    def test_unlisted_ignored(self):
        c = Clock()
        w = WatchdogLogic(["a"], 1.0, c)
        c.t += 1.5
        self.assertFalse(w.beat("b"))
        self.assertFalse(w.ok())

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            WatchdogLogic([], 1.0)


class Geofence(unittest.TestCase):
    def test_statuses(self):
        c = Clock()
        g = GeofenceLogic(SQUARE, 1.0, c)
        self.assertEqual(g.status(), "no_position")
        g.update(5, 5)
        self.assertEqual(g.status(), "ok")
        g.update(11, 5)
        self.assertEqual(g.status(), "outside")
        g.update(float("nan"), 5)
        self.assertEqual(g.status(), "invalid")
        g.update(5, 5)
        c.t += 2
        self.assertEqual(g.status(), "stale")
        self.assertFalse(g.ok())


class EStop(unittest.TestCase):
    def test_latch_and_reset_guard(self):
        e = EmergencyStopLogic()
        self.assertTrue(e.trigger("x"))
        self.assertFalse(e.trigger("y"))
        self.assertTrue(e.active)
        with self.assertRaises(PermissionError):
            e.reset()
        e.allow_reset = True
        e.reset()
        self.assertFalse(e.active)


class Manager(unittest.TestCase):
    def make(self, grace=0.0):
        c = Clock()
        return SafetyManagerLogic(startup_grace=grace, clock=c), c

    def test_normal(self):
        m, _ = self.make()
        healthy(m)
        self.assertEqual(m.evaluate(), SafetyLevel.NORMAL)

    def test_no_inputs_is_safe_mode(self):
        m, _ = self.make()
        self.assertEqual(m.evaluate(), SafetyLevel.SAFE_MODE)

    def test_grace_does_not_latch(self):
        m, c = self.make(grace=5.0)
        self.assertEqual(m.evaluate(), SafetyLevel.SAFE_MODE)
        healthy(m)
        self.assertEqual(m.evaluate(), SafetyLevel.NORMAL)

    def test_estop_latches_even_in_grace(self):
        m, c = self.make(grace=5.0)
        m.update_input("estop", True)
        self.assertEqual(m.evaluate(), SafetyLevel.EMERGENCY_STOP)
        m.update_input("estop", False)
        m.update_input("watchdog", True)
        m.update_input("geofence", True)
        m.update_battery(80)
        self.assertEqual(m.evaluate(), SafetyLevel.EMERGENCY_STOP)

    def test_stale_input_latches_safe_mode(self):
        m, c = self.make()
        healthy(m)
        m.evaluate()
        c.t += 2
        self.assertEqual(m.evaluate(), SafetyLevel.SAFE_MODE)
        healthy(m)
        self.assertEqual(m.evaluate(), SafetyLevel.SAFE_MODE)  # latched

    def test_battery(self):
        m, _ = self.make()
        healthy(m, 20)
        self.assertEqual(m.evaluate(), SafetyLevel.WARNING)
        m.update_battery(10)
        self.assertEqual(m.evaluate(), SafetyLevel.SAFE_MODE)

    def test_invalid_battery_unknown(self):
        m, _ = self.make()
        healthy(m, float("nan"))
        self.assertEqual(m.evaluate(), SafetyLevel.WARNING)

    def test_reset(self):
        m, _ = self.make()
        healthy(m)
        m.update_input("geofence", False)
        self.assertEqual(m.evaluate(), SafetyLevel.SAFE_MODE)
        ok, _msg = m.reset()
        self.assertFalse(ok)
        m.update_input("geofence", True)
        ok, _msg = m.reset()
        self.assertTrue(ok)
        self.assertEqual(m.evaluate(), SafetyLevel.NORMAL)

    def test_reset_after_estop(self):
        m, _ = self.make()
        healthy(m)
        m.update_input("estop", True)
        m.evaluate()
        self.assertFalse(m.reset()[0])
        m.update_input("estop", False)
        self.assertTrue(m.reset()[0])

    def test_unknown_input(self):
        m, _ = self.make()
        with self.assertRaises(ValueError):
            m.update_input("x", True)


if __name__ == "__main__":
    unittest.main()
