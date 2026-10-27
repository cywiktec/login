"""Alert inbox: dedupes, orders by severity, tracks acknowledgement."""

import time
from dataclasses import dataclass, field

SEVERITIES = {"info": 0, "warning": 1, "critical": 2}


@dataclass
class Alert:
    key: str
    severity: str
    message: str
    first_seen: float
    last_seen: float
    count: int = 1
    acknowledged: bool = False


class AlertInbox:
    def __init__(self, max_alerts=100, clock=time.time):
        self.max_alerts = max_alerts
        self._clock = clock
        self._alerts = {}

    def add(self, key, severity, message):
        # Unknown severities are treated as critical rather than hidden.
        if severity not in SEVERITIES:
            severity = "critical"
        now = self._clock()
        alert = self._alerts.get(key)
        if alert:
            alert.count += 1
            alert.last_seen = now
            alert.message = message
            if SEVERITIES[severity] > SEVERITIES[alert.severity]:
                alert.severity = severity
            alert.acknowledged = False  # a repeat needs attention again
        else:
            self._alerts[key] = Alert(key, severity, str(message), now, now)
            self._trim()
        return self._alerts[key]

    def acknowledge(self, key):
        alert = self._alerts.get(key)
        if alert is None:
            return False
        alert.acknowledged = True
        return True

    def active(self):
        """Unacknowledged alerts, most severe then newest first."""
        items = [a for a in self._alerts.values() if not a.acknowledged]
        return sorted(items, key=lambda a: (-SEVERITIES[a.severity], -a.last_seen))

    def has_critical(self):
        return any(a.severity == "critical" for a in self.active())

    def _trim(self):
        # Drop acknowledged, least severe, oldest first; never an unacknowledged critical if avoidable.
        while len(self._alerts) > self.max_alerts:
            victim = min(self._alerts.values(),
                         key=lambda a: (not a.acknowledged, SEVERITIES[a.severity], a.last_seen))
            del self._alerts[victim.key]
