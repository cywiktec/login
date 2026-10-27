"""Plan building and execution. Dry run is the default; nothing changes without execute=True."""

from dataclasses import dataclass
from typing import List

from .docker import steps as docker_steps
from .recovery import load_state, remaining, rollback, save_state
from .ros2 import steps as ros2_steps
from .steps import DryRunRunner, Runner, Step, SystemRunner, run
from .validation import Environment, all_ok, preflight


def build_plan(profile, with_docker=True, with_ros2=True, arch="amd64"):
    steps = [Step("apt-update", "Refresh apt metadata", actions=(run("apt-get", "update"),)),
             Step("base-packages", "Install base packages",
                  actions=(run("apt-get", "install", "-y", f"python{profile.python}", "python3-venv",
                               "python3-pip", "git"),))]
    if with_docker:
        steps += docker_steps(profile)
    if with_ros2:
        steps += ros2_steps(profile, arch)
    ids = [s.id for s in steps]
    assert len(ids) == len(set(ids)), "step ids must be unique"
    return steps


@dataclass
class Result:
    ok: bool
    ran: List[str]
    skipped: List[str]
    failed: str = ""
    error: str = ""
    preflight_failures: tuple = ()


def install(steps, state_path, env: Environment, execute=False, runner: Runner = None,
            rollback_on_failure=False):
    """Preflight, then run the remaining steps in order, saving progress after each.

    - Dry run (default): nothing is executed or saved; the result lists what would run.
    - Failed preflight: nothing runs.
    - Re-running resumes: completed steps are skipped, and a step whose `check` passes is
      marked done without running."""
    checks = preflight(env)
    if execute and not all_ok(checks):
        return Result(False, [], [], preflight_failures=tuple(c for c in checks if not c.ok))

    if runner is None:
        runner = SystemRunner() if execute else DryRunRunner()
    state = load_state(state_path)
    ran, skipped = [], []

    for step in steps:
        if step.id in state.completed:
            skipped.append(step.id)
            continue
        if step.check is not None and runner.check(step.check) == 0:
            skipped.append(step.id)
            if execute:
                state.completed.append(step.id)
                save_state(state_path, state)
            continue
        for action in step.actions:
            rc, output = runner.execute(action)
            if rc != 0:
                state.failed, state.error = step.id, output[-500:]
                if execute:
                    save_state(state_path, state)
                    if rollback_on_failure:
                        rollback(steps, state_path, runner)
                return Result(False, ran, skipped, step.id, state.error)
        ran.append(step.id)
        if execute:
            state.completed.append(step.id)
            state.failed, state.error = None, ""
            save_state(state_path, state)
    return Result(True, ran, skipped)
