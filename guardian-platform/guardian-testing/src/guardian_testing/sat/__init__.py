"""SAT (Site Acceptance Test): checks run against a real or simulated site.

Any exception inside a check is a failure. There is no per-check timeout, so probes
should enforce their own.
"""

import math
from dataclasses import dataclass, field
from typing import Callable, List


@dataclass(frozen=True)
class SatCheck:
    name: str
    fn: Callable
    critical: bool = True  # a failed critical check fails the whole SAT


@dataclass
class SatResult:
    name: str
    passed: bool
    detail: str = ""
    critical: bool = True


@dataclass
class SatReport:
    results: List[SatResult] = field(default_factory=list)

    @property
    def passed(self):
        return bool(self.results) and all(r.passed for r in self.results if r.critical)

    def failures(self):
        return [r for r in self.results if not r.passed]


def run_sat(checks):
    """Each check returns True/False or (bool, detail). Anything else fails."""
    report = SatReport()
    for check in checks:
        try:
            outcome = check.fn()
            ok, detail = outcome if isinstance(outcome, tuple) else (outcome, "")
            ok = ok is True
        except Exception as error:
            ok, detail = False, f"{type(error).__name__}: {error}"
        report.results.append(SatResult(check.name, ok, str(detail), check.critical))
    return report


def _finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def default_checks(probe, min_battery=30.0, max_telemetry_age=5.0):
    """probe: battery_pct(), telemetry_age_s(), geofence_loaded(), watchdog_ok(), estop_roundtrip().
    Thresholds are placeholders to be agreed with the site."""

    def battery():
        v = probe.battery_pct()
        return _finite(v) and v >= min_battery, f"battery {v}"

    def telemetry():
        v = probe.telemetry_age_s()
        return _finite(v) and 0 <= v <= max_telemetry_age, f"telemetry age {v}"

    return [
        SatCheck("battery_sufficient", battery),
        SatCheck("telemetry_fresh", telemetry),
        SatCheck("geofence_loaded", lambda: probe.geofence_loaded()),
        SatCheck("watchdog_ok", lambda: probe.watchdog_ok()),
        SatCheck("estop_roundtrip", lambda: probe.estop_roundtrip()),
    ]
