"""Turn robot health data into Prometheus metrics. Missing or stale data is never exported
as a healthy value: the exporter reports guardian_up 0 and omits the readings."""

import math
import time

from ..prometheus import Metric

STATES = ("INIT", "SELF_TEST", "READY", "MISSION", "RTB", "CHARGING", "SAFE_MODE", "EMERGENCY_STOP")


def _num(value, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    if low is not None and not low <= value <= high:
        return None
    return float(value)


class GuardianExporter:
    def __init__(self, source, stale_after=10.0, clock=time.time, robot="go2-01"):
        """source() -> dict with state, battery_pct, cpu_pct, ram_pct, disk_pct, watchdog_ok
        and 'ts' (when the data was produced). It may raise."""
        self.source = source
        self.stale_after = stale_after
        self._clock = clock
        self.robot = robot

    def collect(self):
        up = Metric("guardian_up", "1 if fresh robot data is available")
        try:
            data = self.source()
        except Exception:
            data = None
        ts = _num(data.get("ts")) if isinstance(data, dict) else None
        age = None if ts is None else self._clock() - ts
        fresh = data is not None and age is not None and 0 <= age <= self.stale_after
        up.add(1 if fresh else 0, robot=self.robot)
        metrics = [up]
        if age is not None:
            metrics.append(Metric("guardian_telemetry_age_seconds", "Age of the latest robot data")
                           .add(max(age, 0.0), robot=self.robot))
        if not fresh:
            return metrics

        state = data.get("state")
        sm = Metric("guardian_state", "1 for the current state")
        for s in STATES:
            sm.add(1 if s == state else 0, robot=self.robot, state=s)
        metrics.append(sm)

        for name, key, help_, high in (
            ("guardian_battery_percent", "battery_pct", "Battery charge", 100),
            ("guardian_cpu_percent", "cpu_pct", "CPU usage", 100),
            ("guardian_ram_percent", "ram_pct", "RAM usage", 100),
            ("guardian_disk_percent", "disk_pct", "Disk usage", 100),
        ):
            value = _num(data.get(key), 0, high)
            if value is not None:
                metrics.append(Metric(name, help_).add(value, robot=self.robot))
        if isinstance(data.get("watchdog_ok"), bool):
            metrics.append(Metric("guardian_watchdog_ok", "1 if the watchdog is healthy")
                           .add(1 if data["watchdog_ok"] else 0, robot=self.robot))
        return metrics
