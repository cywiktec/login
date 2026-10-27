"""Dashboard definitions: panel specs, independent of Grafana's JSON format."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Panel:
    title: str
    expr: str
    kind: str = "timeseries"  # timeseries, stat, gauge
    unit: str = "none"
    min: float = None
    max: float = None
    thresholds: tuple = ()  # ((value, color), ...) ascending; first value is the base


@dataclass(frozen=True)
class Dashboard:
    uid: str
    title: str
    panels: tuple


OVERVIEW = Dashboard("guardian-overview", "MISIEK Guardian overview", (
    Panel("Robot up", "guardian_up", "stat", thresholds=((0, "red"), (1, "green"))),
    Panel("Emergency stop", 'guardian_state{state="EMERGENCY_STOP"}', "stat",
          thresholds=((0, "green"), (1, "red"))),
    Panel("Battery", "guardian_battery_percent", "gauge", "percent", 0, 100,
          ((0, "red"), (10, "orange"), (20, "green"))),
    Panel("Telemetry age", "guardian_telemetry_age_seconds", "timeseries", "s"),
    Panel("CPU", "guardian_cpu_percent", "timeseries", "percent", 0, 100),
    Panel("RAM", "guardian_ram_percent", "timeseries", "percent", 0, 100),
    Panel("Disk", "guardian_disk_percent", "timeseries", "percent", 0, 100,
          ((0, "green"), (80, "orange"), (90, "red"))),
    Panel("Watchdog", "guardian_watchdog_ok", "stat", thresholds=((0, "red"), (1, "green"))),
))

ALL = (OVERVIEW,)
