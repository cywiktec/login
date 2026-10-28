import os
import unittest

import yaml

CONFIG = os.path.join(os.path.dirname(__file__), "..", "config")
FILES = ("emergency_stop", "emergency_reset", "watchdog", "heartbeat", "geofence",
         "safety_rules", "safety_manager", "qos_profiles")


def load(name):
    with open(os.path.join(CONFIG, name + ".yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


class Config(unittest.TestCase):
    def test_all_present_and_parse(self):
        for name in FILES:
            self.assertIsInstance(load(name), dict, name)

    def test_reset_disabled_by_default(self):
        for node in load("emergency_reset").values():
            self.assertIs(node["ros__parameters"]["allow_reset"], False)

    def test_polygon_valid(self):
        from guardian_safety.logic import parse_polygon
        flat = load("geofence")["geofence_node"]["ros__parameters"]["polygon"]
        self.assertEqual(len(parse_polygon(flat)), 4)

    def test_rules_consistent(self):
        p = load("safety_rules")["safety_manager"]["ros__parameters"]
        self.assertLess(p["battery_critical"], p["battery_low"])

    def test_no_param_in_two_files(self):
        seen = {}
        for name in FILES[:-1]:
            for node, body in load(name).items():
                for key in body["ros__parameters"]:
                    self.assertNotIn((node, key), seen, f"{node}.{key} in {name} and {seen.get((node, key))}")
                    seen[(node, key)] = name


if __name__ == "__main__":
    unittest.main()
