import json
import os
import tempfile
import unittest

from guardian_installer.docker import steps as docker_steps
from guardian_installer.installer import build_plan, install
from guardian_installer.profile import detect_profile, parse_os_release
from guardian_installer.recovery import (
    InstallState, load_state, remaining, rollback, rollback_steps, save_state,
)
from guardian_installer.ros2 import steps as ros2_steps
from guardian_installer.steps import DryRunRunner, Run, Runner, Step, Write, run
from guardian_installer.ubuntu22 import PROFILE as U22
from guardian_installer.ubuntu24 import PROFILE as U24
from guardian_installer.validation import Environment, all_ok, preflight

UBUNTU22 = 'NAME="Ubuntu"\nVERSION_ID="22.04"\nID=ubuntu\n'
UBUNTU24 = 'NAME="Ubuntu"\nVERSION_ID="24.04"\nID=ubuntu\n'
GOOD_ENV = Environment(UBUNTU22, "x86_64", 100.0, 8.0, 0)


class FakeRunner(Runner):
    """Records actions; fails any action whose description contains a marker."""

    def __init__(self, fail_on=(), satisfied=()):
        self.log, self.fail_on, self.satisfied = [], fail_on, satisfied

    def execute(self, action):
        self.log.append(action.describe())
        return (1, "boom") if any(m in action.describe() for m in self.fail_on) else (0, "")

    def check(self, action):
        return 0 if any(m in action.describe() for m in self.satisfied) else 1


class ProfileTests(unittest.TestCase):
    def test_detect(self):
        self.assertIs(detect_profile(UBUNTU22), U22)
        self.assertIs(detect_profile(UBUNTU24), U24)
        self.assertEqual((U22.ros_distro, U24.ros_distro), ("humble", "jazzy"))
        for text in ("", "ID=debian\nVERSION_ID=12", 'ID=ubuntu\nVERSION_ID="20.04"', "garbage"):
            self.assertIsNone(detect_profile(text))

    def test_parse(self):
        self.assertEqual(parse_os_release("# c\nA='x'\nB=\"y z\"\nbad")["B"], "y z")


class ValidationTests(unittest.TestCase):
    def failing(self, **kw):
        env = Environment(**{**GOOD_ENV.__dict__, **kw})
        return {c.name for c in preflight(env) if not c.ok}

    def test_good(self):
        self.assertTrue(all_ok(preflight(GOOD_ENV)))

    def test_each_failure(self):
        self.assertEqual(self.failing(os_release=""), {"os"})
        self.assertEqual(self.failing(machine="armv7l"), {"arch"})
        self.assertEqual(self.failing(disk_free_gb=1), {"disk"})
        self.assertEqual(self.failing(ram_gb=0.0), {"ram"})  # unknown RAM fails closed
        self.assertEqual(self.failing(euid=1000), {"root"})
        self.assertFalse(all_ok([]))


class PlanTests(unittest.TestCase):
    def test_unique_ids_and_profile_specifics(self):
        for profile, distro, codename in ((U22, "humble", "jammy"), (U24, "jazzy", "noble")):
            plan = build_plan(profile)
            ids = [s.id for s in plan]
            self.assertEqual(len(ids), len(set(ids)))
            text = " ".join(a.describe() for s in plan for a in s.actions)
            self.assertIn(f"ros-{distro}-ros-base", text)
            writes = [a.content for s in plan for a in s.actions if isinstance(a, Write)]
            self.assertTrue(any(f"{codename} main" in w for w in writes))
            self.assertIn(f"python{profile.python}", text)

    def test_options(self):
        self.assertFalse(any(s.id.startswith("docker") for s in build_plan(U22, with_docker=False)))
        self.assertFalse(any(s.id.startswith("ros2") for s in build_plan(U22, with_ros2=False)))

    def test_commands_are_argv_never_shell(self):
        for s in build_plan(U22):
            for a in (*s.actions, *s.undo):
                self.assertIsInstance(a, (Run, Write))
                if isinstance(a, Run):
                    self.assertIsInstance(a.argv, tuple)
                    self.assertNotIn("sh", a.argv[:1])
                    self.assertTrue(all(isinstance(p, str) for p in a.argv))

    def test_ros_key_over_https_and_signed_source(self):
        text = " ".join(a.describe() for s in ros2_steps(U22) for a in s.actions)
        self.assertIn("https://", text)
        write = [a for s in ros2_steps(U22) for a in s.actions if isinstance(a, Write)][0]
        self.assertIn("signed-by=", write.content)
        self.assertTrue(docker_steps(U22))


class InstallTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = os.path.join(self._tmp.name, "state.json")
        self.steps = [
            Step("a", "A", (run("do", "a"),), (run("undo", "a"),)),
            Step("b", "B", (run("do", "b"),), (run("undo", "b"),), check=run("check", "b")),
            Step("c", "C", (run("do", "c"),), (run("undo", "c"),)),
        ]

    def test_dry_run_is_default_and_changes_nothing(self):
        result = install(self.steps, self.state, GOOD_ENV)
        self.assertTrue(result.ok)
        self.assertEqual(result.ran, ["a", "b", "c"])
        self.assertFalse(os.path.exists(self.state))

    def test_execute_blocked_by_failed_preflight(self):
        runner = FakeRunner()
        result = install(self.steps, self.state, Environment("", "x86_64", 100, 8, 0),
                         execute=True, runner=runner)
        self.assertFalse(result.ok)
        self.assertEqual([c.name for c in result.preflight_failures], ["os"])
        self.assertEqual(runner.log, [])

    def test_execute_runs_in_order_and_saves_progress(self):
        runner = FakeRunner()
        result = install(self.steps, self.state, GOOD_ENV, execute=True, runner=runner)
        self.assertTrue(result.ok)
        self.assertEqual(runner.log, ["do a", "do b", "do c"])
        self.assertEqual(load_state(self.state).completed, ["a", "b", "c"])

    def test_failure_stops_and_resume_skips_done(self):
        runner = FakeRunner(fail_on=["do b"])
        result = install(self.steps, self.state, GOOD_ENV, execute=True, runner=runner)
        self.assertEqual((result.ok, result.failed, result.ran), (False, "b", ["a"]))
        saved = load_state(self.state)
        self.assertEqual((saved.completed, saved.failed), (["a"], "b"))
        self.assertEqual(runner.log, ["do a", "do b"])  # c never ran

        runner2 = FakeRunner()
        result = install(self.steps, self.state, GOOD_ENV, execute=True, runner=runner2)
        self.assertTrue(result.ok)
        self.assertEqual(runner2.log, ["do b", "do c"])
        self.assertEqual(result.skipped, ["a"])
        self.assertIsNone(load_state(self.state).failed)

    def test_satisfied_check_skips_and_records(self):
        runner = FakeRunner(satisfied=["check b"])
        result = install(self.steps, self.state, GOOD_ENV, execute=True, runner=runner)
        self.assertEqual((result.ran, result.skipped), (["a", "c"], ["b"]))
        self.assertIn("b", load_state(self.state).completed)

    def test_rollback_on_failure_undoes_in_reverse(self):
        runner = FakeRunner(fail_on=["do c"])
        result = install(self.steps, self.state, GOOD_ENV, execute=True, runner=runner,
                         rollback_on_failure=True)
        self.assertFalse(result.ok)
        self.assertEqual(runner.log, ["do a", "do b", "do c", "undo b", "undo a"])
        self.assertEqual(load_state(self.state).completed, [])

    def test_failing_undo_does_not_stop_others(self):
        save_state(self.state, InstallState(["a", "b", "c"]))
        runner = FakeRunner(fail_on=["undo b"])
        failed = rollback(self.steps, self.state, runner)
        self.assertEqual(failed, ["b"])
        self.assertEqual(runner.log, ["undo c", "undo b", "undo a"])
        self.assertEqual(load_state(self.state).completed, ["b"])

    def test_corrupt_state_means_start_over(self):
        for content in ("{broken", json.dumps({"completed": "abc"}), json.dumps({"completed": [1]}), "[]"):
            with open(self.state, "w") as f:
                f.write(content)
            self.assertEqual(load_state(self.state).completed, [])
        self.assertEqual(load_state(os.path.join(self._tmp.name, "missing")).completed, [])

    def test_state_write_is_atomic(self):
        save_state(self.state, InstallState(["a"]))
        self.assertEqual(os.listdir(self._tmp.name), ["state.json"])

    def test_helpers(self):
        state = InstallState(["a", "c"])
        self.assertEqual([s.id for s in remaining(self.steps, state)], ["b"])
        self.assertEqual([s.id for s in rollback_steps(self.steps, state)], ["c", "a"])

    def test_dry_run_runner_records(self):
        runner = DryRunRunner()
        install(self.steps, self.state, GOOD_ENV, runner=runner)
        self.assertEqual(runner.log, ["do a", "do b", "do c"])


if __name__ == "__main__":
    unittest.main()
