import math
import unittest

from guardian_go2_driver.battery import BatteryReader
from guardian_go2_driver.control import Controller, Limits
from guardian_go2_driver.dds_bridge import (
    TOPIC_LOW_STATE,
    TOPIC_SPORT_REQUEST,
    DdsBridge,
    InMemoryTransport,
)
from guardian_go2_driver.diagnostics import Diagnostics
from guardian_go2_driver.ros2_bridge import battery_status_msg, health_status_msg
from guardian_go2_driver.telemetry import TelemetryCollector, parse_state


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class BridgeTests(unittest.TestCase):
    def test_publish_subscribe_and_close(self):
        transport = InMemoryTransport()
        bridge = DdsBridge(transport)
        seen = []
        bridge.on_low_state(seen.append)
        transport.publish(TOPIC_LOW_STATE, {"x": 1})
        self.assertEqual(seen, [{"x": 1}])
        bridge.send_sport_request({"api": "StopMove"})
        self.assertEqual(transport.published[-1][0], TOPIC_SPORT_REQUEST)
        bridge.close()
        with self.assertRaises(ConnectionError):
            transport.publish(TOPIC_LOW_STATE, {})


class TelemetryTests(unittest.TestCase):
    GOOD = {"battery_percent": 77, "charging": True, "position": (1, 2, 0), "velocity": (0, 0, 0)}

    def test_parse(self):
        t = parse_state(self.GOOD, now=5.0)
        self.assertEqual((t.battery_percent, t.charging, t.position, t.received_at),
                         (77.0, True, (1.0, 2.0, 0.0), 5.0))

    def test_rejects_bad_data(self):
        for bad in (
            None,
            {},
            {"battery_percent": 101},
            {"battery_percent": -1},
            {"battery_percent": math.nan},
            {"battery_percent": True},
            {"battery_percent": 50, "position": (math.inf, 0, 0)},
        ):
            with self.assertRaises(ValueError, msg=repr(bad)):
                parse_state(bad, now=0)

    def test_collector_freshness_and_rejects(self):
        clock = Clock()
        collector = TelemetryCollector(clock=clock)
        self.assertIsNone(collector.latest())
        collector.handle({"battery_percent": "bad"})
        self.assertEqual(collector.rejected, 1)
        collector.handle(self.GOOD)
        clock.now = 10
        self.assertIsNotNone(collector.latest())
        self.assertIsNone(collector.latest(max_age=2))

    def test_bad_message_keeps_previous_value(self):
        collector = TelemetryCollector(clock=Clock())
        collector.handle(self.GOOD)
        collector.handle({"battery_percent": 500})
        self.assertEqual(collector.latest().battery_percent, 77.0)


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.transport = InMemoryTransport()
        self.clock = Clock()
        self.controller = Controller(
            DdsBridge(self.transport), Limits(0.5, 0.3, 1.0), command_timeout=0.5, clock=self.clock
        )

    def last(self):
        return self.transport.published[-1][1]

    def test_clamps_to_limits(self):
        self.assertTrue(self.controller.move(5, -5, 9))
        self.assertEqual(self.last(), {"api": "Move", "vx": 0.5, "vy": -0.3, "wz": 1.0})

    def test_rejects_non_finite(self):
        for bad in (math.nan, math.inf, "1", None):
            with self.assertRaises(ValueError):
                self.controller.move(bad, 0, 0)
        self.assertEqual(self.transport.published, [])

    def test_deadman_stops_when_stale(self):
        self.controller.move(0.2, 0, 0)
        self.clock.now = 0.4
        self.assertFalse(self.controller.tick())
        self.clock.now = 0.6
        self.assertTrue(self.controller.tick())
        self.assertEqual(self.last(), {"api": "StopMove"})
        self.assertFalse(self.controller.tick())

    def test_zero_command_is_not_moving(self):
        self.controller.move(0, 0, 0)
        self.clock.now = 5
        self.assertFalse(self.controller.tick())

    def test_emergency_stop_latches_until_release(self):
        self.controller.move(0.2, 0, 0)
        self.controller.emergency_stop()
        self.assertEqual(self.last(), {"api": "StopMove"})
        count = len(self.transport.published)
        self.assertFalse(self.controller.move(0.2, 0, 0))
        self.assertEqual(len(self.transport.published), count)
        self.controller.release()
        self.assertTrue(self.controller.move(0.2, 0, 0))

    def test_invalid_timeout(self):
        with self.assertRaises(ValueError):
            Controller(DdsBridge(self.transport), command_timeout=0)


class BatteryAndBridgeMessageTests(unittest.TestCase):
    def test_reader_fresh_and_stale(self):
        clock = Clock()
        collector = TelemetryCollector(clock=clock)
        reader = BatteryReader(collector, max_age=2.0)
        self.assertIsNone(reader.read())
        collector.handle({"battery_percent": 40, "charging": False})
        self.assertEqual(reader.read(), {"percent": 40.0, "plugged": False})
        clock.now = 3
        self.assertIsNone(reader.read())

    def test_messages(self):
        self.assertEqual(battery_status_msg(None),
                         {"has_battery": False, "percent": 0.0, "plugged": False})
        self.assertEqual(battery_status_msg({"percent": 40, "plugged": True}),
                         {"has_battery": True, "percent": 40.0, "plugged": True})
        self.assertEqual(health_status_msg(1, 2, 3),
                         {"cpu_percent": 1.0, "ram_percent": 2.0, "disk_percent": 3.0})


class DiagnosticsTests(unittest.TestCase):
    def build(self):
        transport, clock = InMemoryTransport(), Clock()
        collector = TelemetryCollector(clock=clock)
        controller = Controller(DdsBridge(transport), clock=clock)
        return transport, collector, controller, Diagnostics(transport, collector, controller)

    def test_healthy(self):
        _, collector, _, diagnostics = self.build()
        collector.handle({"battery_percent": 90})
        self.assertTrue(diagnostics.healthy())

    def test_each_failure(self):
        transport, collector, controller, diagnostics = self.build()
        self.assertFalse(diagnostics.healthy())
        collector.handle({"battery_percent": 90})
        controller.emergency_stop()
        failed = {r.name for r in diagnostics.run() if not r.ok}
        self.assertEqual(failed, {"control"})
        transport.close()
        collector.handle({"battery_percent": "bad"})
        failed = {r.name for r in diagnostics.run() if not r.ok}
        self.assertEqual(failed, {"transport", "control", "telemetry_quality"})
