import os
import tempfile
import unittest
from xml.etree import ElementTree as ET

from guardian_digital_twin import gazebo, replay, rviz, scenarios
from guardian_digital_twin.scenarios import SQUARE, Scenario
from guardian_digital_twin.simulation import SimRobot, polygon_contains


class SimulationTests(unittest.TestCase):
    def test_polygon_contains_boundary(self):
        self.assertTrue(polygon_contains(SQUARE, 5, 5))
        self.assertTrue(polygon_contains(SQUARE, 0, 5))
        self.assertFalse(polygon_contains(SQUARE, 11, 5))

    def test_start_outside_rejected(self):
        with self.assertRaises(ValueError):
            SimRobot(20, 20, SQUARE)

    def test_speed_limit_and_battery(self):
        r = SimRobot(1, 1, SQUARE)
        r.step(1.0, (9, 1))
        self.assertAlmostEqual(r.x, 2.0)
        self.assertAlmostEqual(r.battery, 99.5)

    def test_breach_latches_estop(self):
        r = SimRobot(9.5, 5, SQUARE)
        r.step(1.0, (20, 5))
        self.assertTrue(r.breach and r.estopped)
        self.assertEqual(r.x, 9.5)
        r.step(1.0, (5, 5))
        self.assertEqual(r.x, 9.5)

    def test_bad_inputs(self):
        r = SimRobot(1, 1, SQUARE)
        for dt in (0, -1, float("nan"), float("inf"), "1"):
            with self.assertRaises(ValueError):
                r.step(dt, (2, 2))
        with self.assertRaises(ValueError):
            r.step(1, (float("nan"), 0))


class ScenarioTests(unittest.TestCase):
    def test_builtin_scenarios_match_expectations(self):
        for s in scenarios.BUILTIN:
            self.assertEqual(scenarios.validate(s), [], s.name)
            self.assertTrue(scenarios.check(s), s.name)

    def test_geofence_breach_detected(self):
        # a segment between two inside points of a concave polygon can leave the fence
        l_shape = ((0, 0), (10, 0), (10, 2), (2, 2), (2, 10), (0, 10))
        s = Scenario("cut_corner", l_shape, (9, 1), ((1, 9),), expect="geofence_breach")
        self.assertEqual(scenarios.validate(s), [])
        self.assertEqual(scenarios.run(s)[0], "geofence_breach")

    def test_invalid_scenarios_raise(self):
        bad = Scenario("", SQUARE, (50, 50), (), timeout_s=0, events=((1, "teleport"),))
        problems = scenarios.validate(bad)
        self.assertGreaterEqual(len(problems), 5)
        with self.assertRaises(ValueError):
            scenarios.run(bad)

    def test_deterministic(self):
        s = scenarios.BUILTIN[0]
        self.assertEqual(scenarios.run(s), scenarios.run(s))


class ReplayTests(unittest.TestCase):
    def test_roundtrip_and_diff(self):
        _, trace = scenarios.run(scenarios.BUILTIN[0])
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.jsonl")
            replay.save(p, trace)
            loaded = replay.load(p)
        self.assertIsNone(replay.diff(trace, loaded))
        seen = []
        self.assertEqual(replay.replay(loaded, seen.append), len(trace))
        changed = [dict(s) for s in loaded]
        changed[3]["x"] += 1
        self.assertEqual(replay.diff(loaded, changed), 3)
        self.assertEqual(replay.diff(loaded, loaded[:-1]), len(loaded) - 1)

    def test_corrupt_traces_rejected(self):
        good = '{"t":0.1,"x":1,"y":1,"battery":99,"estopped":false}'
        cases = {"json": "{\n", "keys": '{"t":1}\n', "nan": good.replace("99", "NaN") + "\n",
                 "order": good + "\n" + good + "\n", "empty": "",
                 "bool": good.replace('"x":1', '"x":true') + "\n"}
        for name, content in cases.items():
            with tempfile.TemporaryDirectory() as d:
                p = os.path.join(d, "t.jsonl")
                with open(p, "w") as f:
                    f.write(content)
                with self.assertRaises(replay.TraceError, msg=name):
                    replay.load(p)


class ExportTests(unittest.TestCase):
    def test_gazebo_world_is_wellformed(self):
        xml = gazebo.world("guardian", SQUARE)
        root = ET.fromstring(xml)
        self.assertEqual(len(root.findall("./world/model")), 4)
        self.assertEqual(root.find("./world").get("name"), "guardian")

    def test_gazebo_escapes_name_and_rejects_bad_input(self):
        ET.fromstring(gazebo.world('a"<b>&', SQUARE))
        with self.assertRaises(ValueError):
            gazebo.world("w", [(0, 0), (1, 1)])
        with self.assertRaises(ValueError):
            gazebo.world("w", [(0, 0), (0, 0), (1, 1)])

    def test_rviz(self):
        m = rviz.geofence_marker(SQUARE)
        self.assertEqual(len(m["points"]), 5)
        self.assertEqual(len(rviz.waypoint_markers([(1, 1), (2, 2)])), 2)
        self.assertIn("Fixed Frame", rviz.config())
        with self.assertRaises(ValueError):
            rviz.geofence_marker([(0, 0)])


if __name__ == "__main__":
    unittest.main()
