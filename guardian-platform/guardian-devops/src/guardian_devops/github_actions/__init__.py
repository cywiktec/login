"""Generates GitHub Actions workflows for the monorepo and checks them for unsafe patterns."""

from ..yamlout import to_yaml

# Actions are pinned by major tag here; pinning to a commit SHA is stricter (see README).
CHECKOUT = "actions/checkout@v4"
SETUP_PYTHON = "actions/setup-python@v5"


def test_workflow(components, python_versions=("3.10", "3.12")):
    """One matrix job per component; read-only token, no secrets."""
    if not components:
        raise ValueError("no components")
    for c in components:
        if not c.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"bad component name: {c!r}")
    return {
        "name": "guardian-ci",
        "on": {"push": {"branches": ["main"]}, "pull_request": {}},
        "permissions": {"contents": "read"},
        "concurrency": {"group": "ci-${{ github.ref }}", "cancel-in-progress": True},
        "jobs": {
            "test": {
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 15,
                "strategy": {
                    "fail-fast": False,
                    "matrix": {"component": list(components), "python": list(python_versions)},
                },
                "steps": [
                    {"uses": CHECKOUT},
                    {"uses": SETUP_PYTHON, "with": {"python-version": "${{ matrix.python }}"}},
                    {"name": "Test", "run": "make -C guardian-platform/${{ matrix.component }} test"},
                ],
            }
        },
    }


def release_workflow():
    """Runs on tags only; the sole job with write access."""
    return {
        "name": "guardian-release",
        "on": {"push": {"tags": ["v*.*.*"]}},
        "permissions": {"contents": "read"},
        "jobs": {
            "release": {
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 15,
                "permissions": {"contents": "write"},
                "steps": [
                    {"uses": CHECKOUT},
                    {"name": "Check tag matches VERSION",
                     "run": 'test "v$(cat guardian-platform/guardian-core/VERSION)" = "${GITHUB_REF_NAME}"'},
                ],
            }
        },
    }


def render(workflow):
    return to_yaml(workflow)


def lint(workflow):
    """Returns a list of problems; an empty list means no known issue."""
    problems = []
    if "permissions" not in workflow:
        problems.append("missing top-level permissions (default token may be write)")
    elif workflow["permissions"] in ("write-all",):
        problems.append("write-all permissions")
    triggers = workflow.get("on", {})
    if isinstance(triggers, dict) and "pull_request_target" in triggers:
        problems.append("pull_request_target is dangerous with untrusted code")
    for name, job in workflow.get("jobs", {}).items():
        if "timeout-minutes" not in job:
            problems.append(f"job {name}: no timeout")
        for step in job.get("steps", []):
            uses = step.get("uses")
            if uses and "@" not in uses:
                problems.append(f"job {name}: unpinned action {uses}")
            elif uses and uses.endswith(("@main", "@master")):
                problems.append(f"job {name}: action on moving branch {uses}")
            run = step.get("run", "")
            if "${{ github.event" in run:
                problems.append(f"job {name}: event data interpolated into shell (injection)")
    return problems
