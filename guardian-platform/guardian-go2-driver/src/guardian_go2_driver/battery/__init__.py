"""Battery reporting from telemetry."""


class BatteryReader:
    def __init__(self, collector, max_age=2.0):
        self.collector = collector
        self.max_age = max_age

    def read(self):
        """Return {"percent", "plugged"}, or None if there is no fresh data.

        Stale data is reported as missing rather than as the last known value.
        """
        telemetry = self.collector.latest(self.max_age)
        if telemetry is None:
            return None
        return {"percent": telemetry.battery_percent, "plugged": telemetry.charging}
