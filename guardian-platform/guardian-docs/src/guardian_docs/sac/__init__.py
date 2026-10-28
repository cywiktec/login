"""SAC (Site Acceptance Criteria) document: measurable criteria with thresholds."""

from dataclasses import dataclass

from ..markdown import table


@dataclass(frozen=True)
class Criterion:
    id: str
    description: str
    metric: str
    op: str  # "<=" or ">="
    threshold: float

    def __post_init__(self):
        if self.op not in ("<=", ">="):
            raise ValueError(f"bad op: {self.op!r}")

    def passed(self, value):
        """Missing or NaN values fail."""
        if value is None or value != value:
            return False
        return value <= self.threshold if self.op == "<=" else value >= self.threshold


def default_criteria():
    # Placeholders; same values as guardian-testing and to be agreed with the customer.
    return [
        Criterion("SAC-01", "E-stop latency", "estop_latency_s", "<=", 0.5),
        Criterion("SAC-02", "Telemetry age", "telemetry_age_s", "<=", 5.0),
        Criterion("SAC-03", "Battery before mission", "battery_pct", ">=", 30.0),
    ]


def render(criteria):
    return table(["ID", "Criterion", "Metric", "Limit"],
                 [(c.id, c.description, c.metric, f"{c.op} {c.threshold:g}") for c in criteria])


def evaluate(criteria, measurements):
    """Returns {id: bool}; every criterion needs a measurement."""
    return {c.id: c.passed(measurements.get(c.metric)) for c in criteria}
