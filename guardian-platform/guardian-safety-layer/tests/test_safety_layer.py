import unittest

from guardian_safety_layer.battery_guard import BatteryGuard, BatteryLevel
from guardian_safety_layer.estop import EmergencyStop
from guardian_safety_layer.failover import AllHandlersFailed, Failover
from guardian_safety_layer.geofence import Geofence
from guardian_safety_layer.risk_engine import RiskEngine
from guardian_safety_layer.safety_fsm import SafetyFSM, SafetyLevel
from guardian_safety_layer.watchdog import HeartbeatMonitor


class GeofenceTests(unittest.TestCase):
    def setUp(self):
        self.fence = Geofence([(0, 0), (10, 0), (10, 10), (0, 10)])

    def test_inside_outside_and_edge(self):
        self.assertTrue(self.fence.contains(5, 5))
        self.assertFalse(self.fence.contains(11, 5))
        self.assertFalse(self.fence.contains(-0.1, 5))
        self.assertTrue(self.fence.contains(10, 5))
        self.assertTrue(self.fence.contains(0, 0))

    def test_concave_polygon(self):
        fence = Geofence([(0, 0), (10, 0), (10, 10), (5, 5), (0, 10)])
        self.assertTrue(fence.contains(2, 2))
        self.assertFalse(fence.contains(5, 8))

    def test_too_few_vertices(self):
        with self.assertRaises(ValueError):
            Geofence([(0, 0), (1, 1)])


class EmergencyStopTests(unittest.TestCase):
    def test_latches_and_notifies_once(self):
        estop, seen = EmergencyStop(), []
        estop.on_trigger(seen.append)
        self.assertTrue(estop.trigger("operator"))
        self.assertFalse(estop.trigger("again"))
        self.assertEqual(seen, ["operator"])
        self.assertTrue(estop.active)
        self.assertEqual(estop.reason, "operator")

    def test_reset(self):
        estop = EmergencyStop()
        estop.trigger("x")
        estop.reset()
        self.assertFalse(estop.active)
        self.assertIsNone(estop.reason)


class HeartbeatTests(unittest.TestCase):
    def test_expiry_per_source(self):
        now = [0.0]
        monitor = HeartbeatMonitor(timeout=5, clock=lambda: now[0])
        monitor.register("nav")
        monitor.register("core")
        now[0] = 4
        monitor.beat("core")
        self.assertEqual(monitor.expired(), [])
        now[0] = 6
        self.assertEqual(monitor.expired(), ["nav"])

    def test_invalid_timeout(self):
        with self.assertRaises(ValueError):
            HeartbeatMonitor(timeout=0)


class BatteryGuardTests(unittest.TestCase):
    def test_levels(self):
        guard = BatteryGuard(low=30, critical=15)
        self.assertIs(guard.evaluate(80), BatteryLevel.OK)
        self.assertIs(guard.evaluate(30), BatteryLevel.LOW)
        self.assertIs(guard.evaluate(15), BatteryLevel.CRITICAL)
        self.assertIs(guard.evaluate(5, plugged=True), BatteryLevel.OK)
        self.assertIs(guard.evaluate(None), BatteryLevel.UNKNOWN)

    def test_invalid_thresholds(self):
        with self.assertRaises(ValueError):
            BatteryGuard(low=10, critical=20)


class FailoverTests(unittest.TestCase):
    def test_falls_back_in_order(self):
        def broken():
            raise RuntimeError("down")

        self.assertEqual(Failover([("a", broken), ("b", lambda: 42)]).run(), ("b", 42))

    def test_primary_wins(self):
        self.assertEqual(Failover([("a", lambda: 1), ("b", lambda: 2)]).run(), ("a", 1))

    def test_all_fail(self):
        def broken():
            raise RuntimeError("down")

        with self.assertRaises(AllHandlersFailed):
            Failover([("a", broken), ("b", broken)]).run()


class SafetyFSMTests(unittest.TestCase):
    def test_only_escalates(self):
        fsm = SafetyFSM()
        fsm.escalate(SafetyLevel.SAFE_MODE)
        fsm.escalate(SafetyLevel.WARNING)
        self.assertIs(fsm.level, SafetyLevel.SAFE_MODE)

    def test_estop_is_latched(self):
        fsm = SafetyFSM()
        fsm.escalate(SafetyLevel.EMERGENCY_STOP)
        with self.assertRaises(PermissionError):
            fsm.reset()
        fsm.clear_emergency_stop()
        self.assertIs(fsm.level, SafetyLevel.NORMAL)

    def test_reset_from_safe_mode(self):
        fsm = SafetyFSM()
        fsm.escalate(SafetyLevel.SAFE_MODE)
        fsm.reset()
        self.assertIs(fsm.level, SafetyLevel.NORMAL)


class RiskEngineTests(unittest.TestCase):
    def assess(self, **overrides):
        signals = dict(
            estop_active=False,
            inside_geofence=True,
            battery=BatteryLevel.OK,
            expired_heartbeats=[],
        )
        signals.update(overrides)
        return RiskEngine().assess(**signals)

    def test_normal(self):
        self.assertIs(self.assess(), SafetyLevel.NORMAL)

    def test_each_signal(self):
        self.assertIs(self.assess(battery=BatteryLevel.LOW), SafetyLevel.WARNING)
        self.assertIs(self.assess(battery=BatteryLevel.UNKNOWN), SafetyLevel.WARNING)
        self.assertIs(self.assess(battery=BatteryLevel.CRITICAL), SafetyLevel.SAFE_MODE)
        self.assertIs(self.assess(inside_geofence=False), SafetyLevel.SAFE_MODE)
        self.assertIs(self.assess(inside_geofence=None), SafetyLevel.SAFE_MODE)
        self.assertIs(self.assess(expired_heartbeats=["nav"]), SafetyLevel.SAFE_MODE)
        self.assertIs(self.assess(estop_active=True), SafetyLevel.EMERGENCY_STOP)

    def test_estop_dominates(self):
        level = self.assess(estop_active=True, battery=BatteryLevel.LOW)
        self.assertIs(level, SafetyLevel.EMERGENCY_STOP)
