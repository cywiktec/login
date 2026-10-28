import json
import unittest

from guardian_monitoring.alertmanager import DEFAULT_RULES, Rule, RuleError, alertmanager_config, rules_file
from guardian_monitoring.dashboards import ALL
from guardian_monitoring.exporters import GuardianExporter
from guardian_monitoring.grafana import dashboard_json, dashboard_provisioning, datasource_provisioning
from guardian_monitoring.prometheus import Metric, MetricError, render_metrics, scrape_config
from guardian_monitoring.yamlout import to_yaml

try:
    import yaml
except ImportError:  # PyYAML is optional; structure checks are skipped without it
    yaml = None


def parse(text):
    return yaml.safe_load(text)


class YamlTests(unittest.TestCase):
    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_roundtrip(self):
        obj = {"a": [1, 2.5, True, None, "x: y", {"k": ["v", {"n": 1}]}], "b": {}, "c": [],
               "d": "line\nbreak # not comment", "e": [[1, 2], [3]]}
        self.assertEqual(parse(to_yaml(obj)), obj)

    def test_hostile_string_stays_a_string(self):
        text = to_yaml({"k": "v\nevil: true"})
        self.assertEqual(text.count("\n"), 1)


class PrometheusTests(unittest.TestCase):
    def test_render(self):
        m = Metric("guardian_up", "up\nhelp").add(1, robot='a"b\\c\nd')
        text = render_metrics([m, Metric("guardian_x", "x", "counter").add(2.5)])
        self.assertIn("# HELP guardian_up up\\nhelp", text)
        self.assertIn('guardian_up{robot="a\\"b\\\\c\\nd"} 1', text)
        self.assertIn("# TYPE guardian_x counter", text)
        self.assertIn("guardian_x 2.5", text)
        self.assertTrue(text.endswith("\n"))

    def test_rejects_bad_input(self):
        for bad in (float("nan"), float("inf"), True, "1"):
            with self.assertRaises(MetricError):
                Metric("m", "h").add(bad)
        with self.assertRaises(MetricError):
            Metric("m", "h").add(1, **{"bad-label": 1})
        with self.assertRaises(MetricError):
            render_metrics([Metric("bad name", "h")])
        with self.assertRaises(MetricError):
            render_metrics([Metric("ok", "h", "histogram")])

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_scrape_config(self):
        cfg = parse(scrape_config({"guardian": ["exporter:9100"]}))
        self.assertEqual(cfg["scrape_configs"][0]["static_configs"][0]["targets"], ["exporter:9100"])
        self.assertEqual(cfg["rule_files"], ["alerts.yml"])
        with self.assertRaises(MetricError):
            scrape_config({"x": []})


class ExporterTests(unittest.TestCase):
    GOOD = {"state": "READY", "battery_pct": 80, "cpu_pct": 10, "ram_pct": 20, "disk_pct": 30,
            "watchdog_ok": True, "ts": 100.0}

    def values(self, source, now=101.0):
        metrics = GuardianExporter(source, stale_after=5, clock=lambda: now).collect()
        return {m.name: m.samples for m in metrics}

    def test_fresh(self):
        v = self.values(lambda: dict(self.GOOD))
        self.assertEqual(v["guardian_up"], [({"robot": "go2-01"}, 1)])
        self.assertEqual(v["guardian_battery_percent"][0][1], 80.0)
        states = {l["state"]: val for l, val in v["guardian_state"]}
        self.assertEqual(states["READY"], 1)
        self.assertEqual(sum(states.values()), 1)
        self.assertEqual(v["guardian_watchdog_ok"][0][1], 1)

    def test_stale_data_not_exported_as_healthy(self):
        v = self.values(lambda: dict(self.GOOD), now=200.0)
        self.assertEqual(v["guardian_up"][0][1], 0)
        self.assertNotIn("guardian_battery_percent", v)
        self.assertEqual(v["guardian_telemetry_age_seconds"][0][1], 100.0)

    def test_source_failure_and_garbage(self):
        def boom():
            raise RuntimeError

        self.assertEqual(self.values(boom)["guardian_up"][0][1], 0)
        self.assertEqual(self.values(lambda: "x")["guardian_up"][0][1], 0)
        self.assertEqual(self.values(lambda: {"state": "READY"})["guardian_up"][0][1], 0)  # no ts

    def test_invalid_readings_omitted(self):
        data = dict(self.GOOD, battery_pct=250, cpu_pct=float("nan"), watchdog_ok="yes")
        v = self.values(lambda: data)
        for name in ("guardian_battery_percent", "guardian_cpu_percent", "guardian_watchdog_ok"):
            self.assertNotIn(name, v)
        self.assertIn("guardian_ram_percent", v)

    def test_future_timestamp_is_not_fresh(self):
        self.assertEqual(self.values(lambda: dict(self.GOOD, ts=500.0))["guardian_up"][0][1], 0)

    def test_renders(self):
        text = render_metrics(GuardianExporter(lambda: dict(self.GOOD), clock=lambda: 101.0).collect())
        self.assertIn('guardian_state{robot="go2-01",state="READY"} 1', text)


class AlertTests(unittest.TestCase):
    def test_validation(self):
        for rule in (Rule("bad name", "x", "1m", "warning", "s"), Rule("A", " ", "1m", "warning", "s"),
                     Rule("A", "x", "soon", "warning", "s"), Rule("A", "x", "1m", "fatal", "s")):
            with self.assertRaises(RuleError):
                rules_file([rule])
        with self.assertRaises(RuleError):
            rules_file([DEFAULT_RULES[0], DEFAULT_RULES[0]])

    def test_default_rules_cover_critical_cases(self):
        names = {r.alert for r in DEFAULT_RULES}
        self.assertTrue({"GuardianDown", "GuardianEmergencyStop", "GuardianBatteryCritical",
                         "GuardianWatchdogFailed"} <= names)

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_files_parse(self):
        rules = parse(rules_file())["groups"][0]["rules"]
        self.assertEqual(len(rules), len(DEFAULT_RULES))
        self.assertEqual(rules[0]["labels"], {"severity": "critical"})
        self.assertIn("{{ $labels.robot }}", rules[0]["annotations"]["summary"])
        cfg = parse(alertmanager_config("https://hooks.example/x"))
        self.assertEqual(cfg["receivers"][0]["webhook_configs"][0]["url"], "https://hooks.example/x")
        self.assertEqual(cfg["route"]["routes"][0]["matchers"], ['severity="critical"'])

    def test_webhook_must_be_https(self):
        with self.assertRaises(RuleError):
            alertmanager_config("http://insecure")


class GrafanaTests(unittest.TestCase):
    def test_dashboard_json(self):
        for dash in ALL:
            data = json.loads(dashboard_json(dash))
            self.assertEqual(data["uid"], dash.uid)
            self.assertEqual(len(data["panels"]), len(dash.panels))
            ids = [p["id"] for p in data["panels"]]
            self.assertEqual(len(set(ids)), len(ids))
            for p in data["panels"]:
                self.assertEqual(p["datasource"]["uid"], "prometheus")
                steps = p["fieldConfig"]["defaults"]["thresholds"]["steps"]
                self.assertIsNone(steps[0]["value"])

    def test_panel_expressions_use_exported_metrics(self):
        exported = {m.name for m in GuardianExporter(lambda: dict(ExporterTests.GOOD),
                                                     clock=lambda: 101.0).collect()}
        for panel in ALL[0].panels:
            name = panel.expr.split("{")[0]
            self.assertIn(name, exported, panel.title)

    def test_alert_expressions_use_exported_metrics(self):
        exported = {m.name for m in GuardianExporter(lambda: dict(ExporterTests.GOOD),
                                                     clock=lambda: 101.0).collect()}
        for rule in DEFAULT_RULES:
            self.assertIn(rule.expr.split("{")[0].split()[0], exported, rule.alert)

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_provisioning(self):
        ds = parse(datasource_provisioning())["datasources"][0]
        self.assertEqual((ds["type"], ds["uid"]), ("prometheus", "prometheus"))
        self.assertEqual(parse(dashboard_provisioning())["providers"][0]["type"], "file")


if __name__ == "__main__":
    unittest.main()
