"""Install state, resume and rollback. Progress is saved after every step."""

import json
import os
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional

from ..steps import DryRunRunner, Runner, Step


@dataclass
class InstallState:
    completed: List[str] = field(default_factory=list)
    failed: Optional[str] = None
    error: str = ""


def load_state(path):
    """Missing or corrupt state means 'nothing known to be done': steps are re-run, and
    each step's `check` skips work that is already in place."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        done = data["completed"]
        if not isinstance(done, list) or not all(isinstance(s, str) for s in done):
            raise ValueError
        return InstallState(done, data.get("failed"), str(data.get("error", "")))
    except (OSError, ValueError, KeyError, TypeError):
        return InstallState()


def save_state(path, state):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"completed": state.completed, "failed": state.failed, "error": state.error}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def remaining(steps, state):
    return [s for s in steps if s.id not in set(state.completed)]


def rollback_steps(steps, state):
    """Completed steps that can be undone, newest first."""
    done = set(state.completed)
    return [s for s in reversed(steps) if s.id in done and s.undo]


def rollback(steps, state_path, runner: Runner):
    """Run undo actions in reverse order. A failing undo is recorded and the rest still run,
    so one stuck step does not leave everything else half-installed. Returns failed step ids."""
    state = load_state(state_path)
    failed = []
    for step in rollback_steps(steps, state):
        if all(runner.execute(a)[0] == 0 for a in step.undo):
            state.completed.remove(step.id)
        else:
            failed.append(step.id)
    state.failed, state.error = None, ""
    if not isinstance(runner, DryRunRunner):
        save_state(state_path, state)
    return failed
