"""SAT (Site Acceptance Test) procedure document: ordered steps with a sign-off record."""

from dataclasses import dataclass

from ..markdown import table


@dataclass(frozen=True)
class Step:
    id: str
    action: str
    expected: str


def procedure(steps):
    ids = [s.id for s in steps]
    if not steps or len(set(ids)) != len(ids):
        raise ValueError("steps must be non-empty with unique ids")
    return table(["Step", "Action", "Expected", "Result (PASS/FAIL)", "Initials"],
                 [(s.id, s.action, s.expected, "", "") for s in steps])


def default_steps():
    return [
        Step("SAT-01", "Power on, wait for READY", "State READY, self-test passes"),
        Step("SAT-02", "Say 'MISIEK, raport stanu'", "Status reported, no state change"),
        Step("SAT-03", "Say 'MISIEK, rozpocznij patrol' in READY", "State MISSION"),
        Step("SAT-04", "Say 'stop' during mission", "E-stop within the SAC latency limit"),
        Step("SAT-05", "Cut telemetry link", "Robot goes to safe state, alert raised"),
    ]


def signoff(results):
    """results: {step_id: 'PASS'|'FAIL'}. True only if every step is exactly PASS."""
    return bool(results) and all(v == "PASS" for v in results.values())
