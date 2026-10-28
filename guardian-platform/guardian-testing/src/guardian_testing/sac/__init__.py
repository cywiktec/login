"""SAC (Site Acceptance Criteria): measurable pass/fail thresholds for acceptance.

A missing, non-numeric or non-finite measurement fails its criterion.
"""

import math
import operator
from dataclasses import dataclass

OPS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge, "==": operator.eq}


@dataclass(frozen=True)
class Criterion:
    name: str
    metric: str
    op: str
    threshold: float
    required: bool = True

    def __post_init__(self):
        if self.op not in OPS:
            raise ValueError(f"bad operator {self.op!r}")


@dataclass(frozen=True)
class CriterionResult:
    criterion: Criterion
    passed: bool
    measured: object = None
    detail: str = ""


# Placeholders: agree real values with the customer before acceptance.
DEFAULT_CRITERIA = (
    Criterion("estop latency", "estop_latency_s", "<=", 0.5),
    Criterion("telemetry age", "telemetry_age_s", "<=", 5.0),
    Criterion("battery at start", "battery_pct", ">=", 30.0),
    Criterion("geofence violations", "geofence_violations", "==", 0),
    Criterion("watchdog trips", "watchdog_trips", "==", 0),
    Criterion("mission completion rate", "mission_completion_rate", ">=", 0.95, required=False),
)


def evaluate(criteria, measurements):
    """Returns (accepted, [CriterionResult]). Accepted needs every required criterion to pass,
    and at least one required criterion to exist."""
    results = []
    for c in criteria:
        value = measurements.get(c.metric)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            results.append(CriterionResult(c, False, value, "missing or invalid measurement"))
            continue
        ok = OPS[c.op](value, c.threshold)
        results.append(CriterionResult(c, ok, value, "" if ok else f"{value} not {c.op} {c.threshold}"))
    required = [r for r in results if r.criterion.required]
    return bool(required) and all(r.passed for r in required), results
