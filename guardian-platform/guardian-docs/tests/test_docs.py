import os
import unittest

from guardian_docs import architecture, build, fmea, markdown, nza, rtm, sac, sat, ukdp
from guardian_docs.fmea import FailureMode, v2


class MarkdownTests(unittest.TestCase):
    def test_pipe_and_newline_escaped(self):
        out = markdown.table(["a"], [("x|y\nz",)])
        self.assertIn("x\\|y z", out)
        with self.assertRaises(ValueError):
            markdown.table(["a", "b"], [("1",)])


class FmeaTests(unittest.TestCase):
    def test_rpn_and_ordering(self):
        modes = [FailureMode("A", "c", "m", "e", 2, 2, 2), FailureMode("B", "c", "m", "e", 5, 5, 5, "x")]
        self.assertEqual(modes[1].rpn, 125)
        out = fmea.render(modes)
        self.assertLess(out.index("| B "), out.index("| A "))

    def test_ratings_validated(self):
        for bad in (0, 11, 2.5, True, "3"):
            with self.assertRaises(ValueError):
                FailureMode("A", "c", "m", "e", bad, 1, 1)
        with self.assertRaises(ValueError):
            FailureMode("", "c", "m", "e", 1, 1, 1)

    def test_high_severity_needs_action_even_with_low_rpn(self):
        m = FailureMode("A", "c", "m", "e", 10, 1, 1)
        self.assertTrue(m.needs_action)
        self.assertEqual(fmea.validate([m]), ["A: needs action but has no mitigation"])

    def test_duplicate_ids(self):
        m = FailureMode("A", "c", "m", "e", 1, 1, 1)
        self.assertEqual(fmea.validate([m, m]), ["duplicate id A"])

    def test_initial_modes_are_consistent(self):
        self.assertEqual(fmea.validate(fmea.initial_modes()), [])


class RtmTests(unittest.TestCase):
    def test_validate_and_coverage(self):
        reqs = [rtm.Requirement("R1", "t", "c", ("t1",)), rtm.Requirement("R2", "t", "c"),
                rtm.Requirement("R3", "t", "c", ("ghost",))]
        self.assertEqual(rtm.validate(reqs, {"t1"}),
                         ["R2: no test", "R3: unknown test ghost"])
        self.assertAlmostEqual(rtm.coverage(reqs, {"t1"}), 1 / 3)
        self.assertEqual(rtm.coverage([]), 0.0)
        self.assertIn("**NONE**", rtm.render(reqs))

    def test_duplicate(self):
        r = rtm.Requirement("R1", "t", "c", ("t",))
        self.assertEqual(rtm.validate([r, r]), ["duplicate id R1"])


class RegisterTests(unittest.TestCase):
    def test_lifecycle(self):
        reg = nza.new_register()
        reg.add(nza.Document("D1", "Plan", "ola"))
        with self.assertRaises(ValueError):
            reg.add(nza.Document("D1", "Again", "ola"))
        with self.assertRaises(ValueError):
            reg.transition("D1", "approved", "ewa")  # must pass review first
        reg.transition("D1", "review")
        with self.assertRaises(PermissionError):
            reg.transition("D1", "approved", "ola")
        with self.assertRaises(PermissionError):
            reg.transition("D1", "approved")
        reg.transition("D1", "approved", "ewa")
        self.assertEqual(reg.get("D1").status, "approved")
        self.assertIn("# NZA", reg.render())

    def test_validation_and_ukdp(self):
        with self.assertRaises(ValueError):
            nza.Document("D", "t", "o", status="weird")
        with self.assertRaises(ValueError):
            nza.Document("D", "", "o")
        self.assertIn("# UKDP", ukdp.new_register().render())


class SatSacTests(unittest.TestCase):
    def test_signoff_fail_closed(self):
        self.assertTrue(sat.signoff({"a": "PASS"}))
        self.assertFalse(sat.signoff({}))
        self.assertFalse(sat.signoff({"a": "PASS", "b": "pass"}))
        self.assertFalse(sat.signoff({"a": "PASS", "b": None}))

    def test_procedure(self):
        self.assertIn("SAT-04", sat.procedure(sat.default_steps()))
        with self.assertRaises(ValueError):
            sat.procedure([])
        s = sat.Step("x", "a", "b")
        with self.assertRaises(ValueError):
            sat.procedure([s, s])

    def test_criteria(self):
        crit = sac.default_criteria()
        ok = {"estop_latency_s": 0.2, "telemetry_age_s": 1, "battery_pct": 80}
        self.assertTrue(all(sac.evaluate(crit, ok).values()))
        bad = dict(ok, estop_latency_s=float("nan"))
        del bad["battery_pct"]
        res = sac.evaluate(crit, bad)
        self.assertFalse(res["SAC-01"])
        self.assertFalse(res["SAC-03"])
        self.assertTrue(res["SAC-02"])
        with self.assertRaises(ValueError):
            sac.Criterion("x", "d", "m", "<", 1)
        self.assertIn("<= 0.5", sac.render(crit))


class ArchitectureTests(unittest.TestCase):
    def test_default_map_is_acyclic_and_complete(self):
        self.assertIsNone(architecture.find_cycle(architecture.DEPENDENCIES))
        self.assertEqual(architecture.undefined(architecture.DEPENDENCIES), [])

    def test_cycle_found(self):
        cyc = architecture.find_cycle({"a": ["b"], "b": ["c"], "c": ["a"]})
        self.assertEqual(cyc[0], cyc[-1])
        self.assertEqual(set(cyc), {"a", "b", "c"})

    def test_undefined_and_mermaid(self):
        self.assertEqual(architecture.undefined({"a": ["x"]}), ["x"])
        self.assertTrue(architecture.mermaid({"a-b": ["c"]}).startswith("graph TD\n    a_b[a-b] --> c[c]"))


class ControlledDocumentTests(unittest.TestCase):
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def read(self, *parts):
        with open(os.path.join(self.ROOT, *parts), encoding="utf-8") as f:
            return f.read()

    def test_documents_conform_to_ukdp(self):
        for rel in (("docs", "fmea", "FMEA-v2.0.md"), ("docs", "nza", "NZA-v1.0.md"),
                    ("docs", "ukdp", "UKDP-v1.0.md")):
            self.assertEqual(ukdp.check(self.read(*rel)), [], rel)

    def test_ukdp_check_finds_problems(self):
        problems = " | ".join(ukdp.check("no title\n**ID:** X-1\n**Status:** ok\n"))
        for word in ("tytułu", "Wersja", "ID", "status", "sekcji: Cel"):
            self.assertIn(word, problems)

    def test_fmea_v2_is_valid_and_complete(self):
        modes = v2.modes()
        self.assertEqual(fmea.validate(modes), [])
        self.assertGreaterEqual(len(modes), 30)
        self.assertEqual(len({m.id for m in modes}), len(modes))
        # any unverified high-risk mode must be openly listed as a gap
        gaps = fmea.unverified(modes)
        self.assertTrue(set(gaps) >= {"F-009", "F-030", "F-035"})

    def test_generated_fmea_is_up_to_date(self):
        self.assertEqual(self.read("docs", "fmea", "FMEA-v2.0.md"), build.render(),
                         "run: PYTHONPATH=src python3 -m guardian_docs.build .")


if __name__ == "__main__":
    unittest.main()
