"""FMEA: failure modes with Severity x Occurrence x Detection = RPN (each 1-10)."""

from dataclasses import dataclass

from ..markdown import table

RPN_LIMIT = 100  # placeholder action threshold; to be set by the safety owner


@dataclass(frozen=True)
class FailureMode:
    id: str
    component: str
    mode: str
    effect: str
    severity: int
    occurrence: int
    detection: int  # 10 = practically undetectable
    mitigation: str = ""
    verified_by: str = ""  # test or evidence reference; empty = not verified(self):
    def __post_init__(self):
        for f in ("severity", "occurrence", "detection"):
            v = getattr(self, f)
            if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 10:
                raise ValueError(f"{f} must be an integer 1-10, got {v!r}")
        if not self.id or not self.mode:
            raise ValueError("id and mode are required")

    @property
    def rpn(self):
        return self.severity * self.occurrence * self.detection

    @property
    def needs_action(self):
        # Severity 9-10 needs action regardless of RPN.
        return self.rpn >= RPN_LIMIT or self.severity >= 9


def validate(modes):
    problems = []
    seen = set()
    for m in modes:
        if m.id in seen:
            problems.append(f"duplicate id {m.id}")
        seen.add(m.id)
        if m.needs_action and not m.mitigation:
            problems.append(f"{m.id}: needs action but has no mitigation")
    return problems


def render(modes):
    ordered = sorted(modes, key=lambda m: (-m.rpn, m.id))
    return table(["ID", "Component", "Failure mode", "Effect", "S", "O", "D", "RPN", "Action", "Mitigation",
                  "Verified by"],
                 [(m.id, m.component, m.mode, m.effect, m.severity, m.occurrence, m.detection,
                   m.rpn, "YES" if m.needs_action else "no", m.mitigation or "-", m.verified_by or "-")
                  for m in ordered])


def unverified(modes):
    """Modes that need action but cite no verification evidence."""
    return sorted(m.id for m in modes if m.needs_action and not m.verified_by)


def initial_modes():
    """Draft entries; the ratings are my estimates and must be reviewed."""
    return [
        FailureMode("F-01", "go2-driver", "Telemetry stops", "Stale state used for decisions", 8, 4, 3,
                    "Staleness check fails closed (watchdog)"),
        FailureMode("F-02", "safety-layer", "E-stop not delivered", "Robot keeps moving", 10, 2, 4,
                    "E-stop allowed from any state/source; latency SAC"),
        FailureMode("F-03", "ai-engine", "LLM misreads intent", "Wrong actuating command", 8, 5, 4,
                    "Confidence >= 0.8 and state policy"),
        FailureMode("F-04", "backup", "Snapshot torn on power loss", "Lost resume point", 5, 3, 2,
                    "Atomic write + hash verify"),
    ]
