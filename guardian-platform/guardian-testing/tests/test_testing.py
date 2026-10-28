import math
import os
import tempfile
import unittest

from guardian_ai_engine.intent_parser import Intent
from guardian_ai_engine.policy_engine import Decision, PolicyEngine
from guardian_backup.journaling import Journal
from guardian_backup.recovery import plan_auto_resume, recover_state
from guardian_backup.snapshot import SnapshotStore
from guardian_monitoring.exporters import GuardianExporter
from guardian_monitoring.grafana import dashboard_json
from guardian_monitoring.dashboards import OVERVIEW
from guardian_monitoring.prometheus import render_metrics
from guardian_safety_layer.safety_fsm import SafetyFSM, SafetyLevel
from guardian_telemetry.message import make_message
from guardian_telemetry.mqtt import InMemoryBroker
from guardian_telemetry.snapshots import SnapshotCache
from guardian_telemetry.websocket import Hub
from guardian_voice.speech_to_text import Transcript
from guardian_web.fleet import EMERGENCY, FleetRegistry

from guardian_testing.integration import FakeRobot, Stack
from guardian_testing.load import LoadResult, percentile, run_load, violations
from guardian_testing.regression import GoldenMismatch, check_golden
from guardian_testing.safety import check_policy_invariants, check_safety_fsm_invariants
from guardian_testing.sac import DEFAULT_CRITERIA, Criterion, evaluate
from guardian_testing.sat import SatCheck, default_checks, run_sat

GOLDEN = os.path.join(os.path.dirname(__file__), "golden")


# ---------------------------------------------------------------- SAT / SAC

class FakeProbe:
    def __init__(self, **over):
        self.values = dict(battery=80.0, age=1.0, fence=True, wd=True, estop=True)
        self.values.update(over)

    def battery_pct(self):
        return self.values["battery"]

    def telemetry_age_s(self):
        return self.values["age"]

    def geofence_loaded(self):
        return self.values["fence"]

    def watchdog_ok(self):
        return self.values["wd"]

    def estop_roundtrip(self):
        return self.values["estop"]


class SatTests(unittest.TestCase):
    def test_pass(self):
        report = run_sat(default_checks(FakeProbe()))
        self.assertTrue(report.passed)
        self.assertEqual(report.failures(), [])

    def test_each_failure_fails_sat(self):
        for over in (dict(battery=10.0), dict(battery=float("nan")), dict(age=99), dict(age=-1),
                     dict(fence=False), dict(wd=False), dict(estop=False), dict(battery=None)):
            self.assertFalse(run_sat(default_checks(FakeProbe(**over))).passed, over)

    def test_exception_and_truthy_values_fail(self):
        def boom():
            raise RuntimeError("probe offline")

        report = run_sat([SatCheck("a", boom), SatCheck("b", lambda: 1), SatCheck("c", lambda: (True, "ok"))])
        self.assertEqual([r.passed for r in report.results], [False, False, True])
        self.assertIn("probe offline", report.results[0].detail)

    def test_empty_and_noncritical(self):
        self.assertFalse(run_sat([]).passed)
        report = run_sat([SatCheck("a", lambda: True), SatCheck("n", lambda: False, critical=False)])
        self.assertTrue(report.passed)
        self.assertEqual(len(report.failures()), 1)


class SacTests(unittest.TestCase):
    GOOD = dict(estop_latency_s=0.2, telemetry_age_s=1, battery_pct=90, geofence_violations=0,
                watchdog_trips=0)

    def test_accepts(self):
        accepted, results = evaluate(DEFAULT_CRITERIA, self.GOOD)
        self.assertTrue(accepted)
        self.assertEqual(len(results), len(DEFAULT_CRITERIA))

    def test_missing_measurement_fails(self):
        for key in self.GOOD:
            data = {k: v for k, v in self.GOOD.items() if k != key}
            self.assertFalse(evaluate(DEFAULT_CRITERIA, data)[0], key)

    def test_bad_values_fail(self):
        for bad in (float("nan"), float("inf"), True, "0", None):
            self.assertFalse(evaluate(DEFAULT_CRITERIA, {**self.GOOD, "watchdog_trips": bad})[0], bad)

    def test_threshold_violation_and_optional(self):
        self.assertFalse(evaluate(DEFAULT_CRITERIA, {**self.GOOD, "estop_latency_s": 0.9})[0])
        self.assertFalse(evaluate(DEFAULT_CRITERIA, {**self.GOOD, "geofence_violations": 1})[0])
        self.assertTrue(evaluate(DEFAULT_CRITERIA, {**self.GOOD, "mission_completion_rate": 0.1})[0])

    def test_no_required_criteria_is_not_accepted(self):
        self.assertFalse(evaluate([Criterion("x", "m", ">", 0, required=False)], {"m": 1})[0])
        self.assertFalse(evaluate([], {})[0])

    def test_bad_operator(self):
        with self.assertRaises(ValueError):
            Criterion("x", "m", "!=", 0)


# --------------------------------------------------------------- integration

class IntegrationTests(unittest.TestCase):
    def test_voice_patrol_runs_diagnostics_first(self):
        stack = Stack(["MISIEK, rozpocznij patrol."])
        result = stack.utter()
        self.assertEqual(result.status, "handled")
        self.assertEqual(stack.robot.calls, ["run_diagnostics", "start_patrol"])
        self.assertEqual(stack.robot.state, "MISSION")
        self.assertEqual(stack.tts.spoken, ["run_diagnostics:executed, start_patrol:executed"])

    def test_command_denied_in_wrong_state(self):
        stack = Stack(["MISIEK, rozpocznij patrol.", "MISIEK, rozpocznij patrol."])
        stack.utter()
        stack.utter()  # already in MISSION
        self.assertEqual(stack.robot.calls.count("start_patrol"), 1)
        self.assertEqual(stack.last_results[-1].status, "denied")  # diagnostics ran, patrol did not_reaches_the_robot_and_latches(self):
        stack = Stack(["MISIEK, rozpocznij patrol.", "stop"])
        stack.utter()
        stack.utter()
        self.assertEqual(stack.robot.state, "EMERGENCY_STOP")
        self.assertTrue(stack.robot.estop.active)
        self.assertEqual(stack.robot.safety.level, SafetyLevel.EMERGENCY_STOP)

    def test_no_actuation_after_estop_until_explicit_recover(self):
        stack = Stack(["stop", "MISIEK, rozpocznij patrol.", "MISIEK, wznów po awarii."])
        stack.utter()
        stack.utter()
        self.assertNotIn("start_patrol", stack.robot.calls)
        stack.utter()
        self.assertEqual(stack.robot.state, "READY")
        self.assertFalse(stack.robot.estop.active)

    def test_llm_cannot_recover_from_estop(self):
        llm = ['{"intent": "recover", "confidence": 1.0}']
        stack = Stack(["stop", "MISIEK, proszę wznowić po awarii"], llm_responses=llm)
        stack.utter()
        stack.utter()
        self.assertEqual(stack.robot.state, "EMERGENCY_STOP")
        self.assertEqual(stack.last_results[0].status, "denied")

    def test_llm_patrol_needs_confidence(self):
        low = Stack(["MISIEK, ruszaj w obchód"], llm_responses=['{"intent": "start_patrol", "confidence": 0.7}'])
        low.utter()
        self.assertEqual(low.robot.state, "READY")
        high = Stack(["MISIEK, ruszaj w obchód"], llm_responses=['{"intent": "start_patrol", "confidence": 0.9}'])
        high.utter()
        self.assertEqual(high.robot.state, "MISSION")

    def test_low_stt_confidence_does_nothing(self):
        stack = Stack([Transcript("MISIEK, rozpocznij patrol", 0.2)])
        self.assertEqual(stack.utter().status, "low_confidence")
        self.assertEqual(stack.robot.calls, [])

    def test_router_decisions_are_logged(self):
        stack = Stack(["MISIEK, raport stanu."])
        stack.utter()
        self.assertEqual(stack.memory.last("command")["data"]["status"], "executed")

    def test_telemetry_to_fleet_and_cache(self):
        broker, cache, hub = InMemoryBroker(), SnapshotCache(), Hub()
        client = hub.connect()
        broker.subscribe("guardian/#", lambda topic, m: (cache.update(m), hub.broadcast(m)))
        clock = [1000.0]
        fleet = FleetRegistry(clock=lambda: clock[0])

        def to_fleet(topic, m):
            fleet.heartbeat(m.robot_id, m.data["state"], m.data.get("battery_pct"))

        broker.subscribe("guardian/+/state", to_fleet)
        broker.publish_message(make_message("go2-01", "state", 1.0, {"state": "EMERGENCY_STOP", "battery_pct": 50}))
        self.assertEqual(fleet.status("go2-01"), EMERGENCY)
        self.assertEqual(cache.get("go2-01", "state").data["state"], "EMERGENCY_STOP")
        self.assertEqual(len(client.drain()), 1)

    def test_exporter_reflects_stale_telemetry_through_alert_metrics(self):
        data = {"state": "READY", "battery_pct": 80, "ts": 100.0}
        text = render_metrics(GuardianExporter(lambda: data, stale_after=5, clock=lambda: 200.0).collect())
        self.assertIn('guardian_up{robot="go2-01"} 0', text)
        self.assertNotIn("guardian_battery_percent", text)

    def test_backup_roundtrip_and_resume(self):
        with tempfile.TemporaryDirectory() as d:
            store = SnapshotStore(d)
            journal = Journal(os.path.join(d, "j.log"))
            try:
                journal.append({"state": "MISSION"})
                store.save({"state": "MISSION", "checkpoint": {"wp": 2}}, journal.last_seq)
                journal.append({"state": "MISSION", "checkpoint": {"wp": 3}})
                rec = recover_state(store, journal, lambda s, e: {**s, **e})
                plan = plan_auto_resume(rec, saved_at=100.0, now=110.0)
            finally:
                journal.close()
        self.assertEqual((plan.action, plan.checkpoint), ("resume", {"wp": 3}))


# --------------------------------------------------------------------- safety

class SafetyInvariantTests(unittest.TestCase):
    def test_real_policy_holds(self):
        self.assertEqual(check_policy_invariants(PolicyEngine()), [])

    def test_real_fsm_holds(self):
        self.assertEqual(check_safety_fsm_invariants(), [])

    def test_checker_catches_permissive_policy(self):
        class AllowAll:
            def evaluate(self, intent, state):
                return Decision(True, "yes")

        violations_ = check_policy_invariants(AllowAll())
        self.assertTrue(any("unknown intent" in v for v in violations_))
        self.assertTrue(any("LLM-sourced recover" in v for v in violations_))
        self.assertTrue(any("unknown state" in v for v in violations_))

    def test_checker_catches_blocked_stop(self):
        class NoStop(PolicyEngine):
            def evaluate(self, intent, state):
                if intent.name == "emergency_stop" and state == "MISSION":
                    return Decision(False, "bug")
                return super().evaluate(intent, state)

        self.assertTrue(any("emergency_stop denied" in v for v in check_policy_invariants(NoStop())))

    def test_checker_catches_resettable_estop(self):
        class Leaky(SafetyFSM):
            def reset(self):
                self._level = SafetyLevel.NORMAL

        self.assertTrue(check_safety_fsm_invariants(Leaky))

    def test_robot_stop_is_idempotent_and_listeners_fire_once(self):
        robot = FakeRobot()
        self.assertTrue(robot.estop.trigger("a"))
        self.assertFalse(robot.estop.trigger("b"))
        self.assertEqual(robot.state, "EMERGENCY_STOP")


# ------------------------------------------------------------------------ load

class LoadTests(unittest.TestCase):
    def test_percentile(self):
        self.assertEqual(percentile([], 99), 0.0)
        self.assertEqual(percentile([5], 50), 5)
        data = list(range(1, 101))
        self.assertEqual((percentile(data, 50), percentile(data, 95), percentile(data, 100)), (50, 95, 100))

    def test_counts_and_errors(self):
        def fn(i):
            if i % 10 == 0:
                raise RuntimeError

        result = run_load(fn, 100, threads=4)
        self.assertEqual((result.count, result.errors, len(result.durations)), (100, 10, 100))
        self.assertAlmostEqual(result.error_rate, 0.1)
        self.assertTrue(violations(result))
        self.assertEqual(violations(result, max_error_rate=0.2), [])

    def test_all_indices_run_exactly_once(self):
        seen = []
        run_load(seen.append, 50, threads=7)
        self.assertEqual(sorted(seen), list(range(50)))

    def test_thresholds(self):
        slow = LoadResult(10, 0, 100.0, [1.0] * 10)
        self.assertEqual(len(violations(slow, max_p99_s=0.5, min_throughput=1)), 2)
        self.assertEqual(LoadResult(0, 0, 0.0).error_rate, 1.0)  # no data is not a pass

    def test_invalid(self):
        with self.assertRaises(ValueError):
            run_load(lambda i: None, 0)

    def test_telemetry_pipeline_under_load(self):
        broker, hub = InMemoryBroker(), Hub()
        client = hub.connect(max_queue=50)
        broker.subscribe("guardian/#", lambda t, m: hub.broadcast(m))

        def publish(i):
            broker.publish_message(make_message("go2-01", "pose", float(i), {"x": i}))

        result = run_load(publish, 2000, threads=4)
        self.assertEqual(violations(result), [])
        self.assertEqual(len(client.drain()), 50)  # bounded queue, nothing blocked
        self.assertEqual(client.dropped, 1950)
        self.assertEqual(broker.rejected, 0)


# ------------------------------------------------------------------ regression

class RegressionTests(unittest.TestCase):
    def test_intent_table_is_stable(self):
        from guardian_ai_engine.intent_parser import IntentParser

        phrases = ["MISIEK, raport stanu.", "MISIEK, poziom baterii.", "MISIEK, raport baterii.",
                   "MISIEK, rozpocznij patrol.", "MISIEK, wróć do bazy.", "MISIEK, zatrzymaj misję.",
                   "MISIEK, uruchom diagnostykę.", "MISIEK, wykonaj snapshot.", "MISIEK, wznów po awarii.",
                   "MISIEK, wykryj ruch.", "stop", "misja", "rtb", "co słychać", ""]
        parser = IntentParser()
        table = {p: parser.parse(p).name for p in phrases}
        check_golden("intents", table, GOLDEN)

    def test_prometheus_output_is_stable(self):
        data = {"state": "MISSION", "battery_pct": 55.5, "cpu_pct": 12, "ram_pct": 30, "disk_pct": 40,
                "watchdog_ok": True, "ts": 100.0}
        text = render_metrics(GuardianExporter(lambda: data, clock=lambda: 101.0).collect())
        check_golden("prometheus_metrics", {"text": text}, GOLDEN)

    def test_grafana_dashboard_is_stable(self):
        import json
        check_golden("grafana_overview", json.loads(dashboard_json(OVERVIEW)), GOLDEN)

    def test_missing_golden_is_a_failure_not_created(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(GoldenMismatch):
                check_golden("nope", {"a": 1}, d, update=False)
            self.assertEqual(os.listdir(d), [])

    def test_mismatch_detected_and_update(self):
        with tempfile.TemporaryDirectory() as d:
            check_golden("x", {"a": 1}, d, update=True)
            check_golden("x", {"a": 1}, d, update=False)
            with self.assertRaises(GoldenMismatch):
                check_golden("x", {"a": 2}, d, update=False)

    def test_bad_golden_name(self):
        for name in ("../x", ".hidden", "a/b"):
            with self.assertRaises(ValueError):
                check_golden(name, {}, "/tmp", update=False)


if __name__ == "__main__":
    unittest.main()
