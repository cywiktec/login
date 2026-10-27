"""Step model and command runners. Commands are argv lists, never shell strings."""

import os
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Run:
    argv: Tuple[str, ...]

    def describe(self):
        return " ".join(self.argv)


@dataclass(frozen=True)
class Write:
    path: str
    content: str
    mode: int = 0o644

    def describe(self):
        return f"write {self.path}"


@dataclass(frozen=True)
class Step:
    id: str
    description: str
    actions: Tuple = ()
    undo: Tuple = ()
    check: Optional[Run] = None  # if it exits 0, the step is already satisfied and is skipped


def run(*argv):
    return Run(tuple(argv))


class Runner:
    def execute(self, action):
        """Returns (returncode, output)."""
        raise NotImplementedError


class DryRunRunner(Runner):
    """Records what would happen and changes nothing. `check` commands report 'not satisfied'."""

    def __init__(self, check_rc=1):
        self.log = []
        self.check_rc = check_rc

    def execute(self, action):
        self.log.append(action.describe())
        return 0, ""

    def check(self, action):
        return self.check_rc


class SystemRunner(Runner):
    """Really executes. Only used when the caller passes execute=True to the installer."""

    def __init__(self, timeout=1800):
        self.timeout = timeout

    def execute(self, action):
        if isinstance(action, Write):
            try:
                with open(action.path, "w", encoding="utf-8") as f:
                    f.write(action.content)
                os.chmod(action.path, action.mode)
            except OSError as error:
                return 1, str(error)
            return 0, ""
        try:
            done = subprocess.run(list(action.argv), capture_output=True, text=True,
                                  timeout=self.timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            return 127, str(error)
        return done.returncode, (done.stdout + done.stderr)[-4000:]

    def check(self, action):
        return self.execute(action)[0]
