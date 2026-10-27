"""Alert rules and Alertmanager config generation."""

import re
from dataclasses import dataclass

from ..yamlout import to_yaml

SEVERITIES = ("info", "warning", "critical")
ALERT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
DURATION = re.compile(r"^\d+(ms|s|m|h|d)$")


class RuleError(ValueError):
    pass


@dataclass(frozen=True)
class Rule:
    alert: str
    expr: str
    for_: str
    severity: str
    summary: str

    def validate(self):
        if not ALERT_NAME.match(self.alert):
            raise RuleError(f"bad alert name {self.alert!r}")
        if not self.expr.strip():
            raise RuleError(f"{self.alert}: empty expression")
        if not DURATION.match(self.for_):
            raise RuleError(f"{self.alert}: bad duration {self.for_!r}")
        if self.severity not in SEVERITIES:
            raise RuleError(f"{self.alert}: bad severity {self.severity!r}")


# Thresholds are untuned placeholders.
DEFAULT_RULES = (
    Rule("GuardianDown", "guardian_up == 0", "30s", "critical", "No fresh data from {{ $labels.robot }}"),
    Rule("GuardianEmergencyStop", 'guardian_state{state="EMERGENCY_STOP"} == 1', "0s", "critical",
         "{{ $labels.robot }} is in EMERGENCY_STOP"),
    Rule("GuardianSafeMode", 'guardian_state{state="SAFE_MODE"} == 1', "1m", "warning",
         "{{ $labels.robot }} is in SAFE_MODE"),
    Rule("GuardianBatteryCritical", "guardian_battery_percent < 10", "1m", "critical",
         "Battery below 10% on {{ $labels.robot }}"),
    Rule("GuardianBatteryLow", "guardian_battery_percent < 20", "2m", "warning",
         "Battery below 20% on {{ $labels.robot }}"),
    Rule("GuardianWatchdogFailed", "guardian_watchdog_ok == 0", "10s", "critical",
         "Watchdog unhealthy on {{ $labels.robot }}"),
    Rule("GuardianDiskAlmostFull", "guardian_disk_percent > 90", "5m", "warning",
         "Disk above 90% on {{ $labels.robot }}"),
)


def rules_file(rules=DEFAULT_RULES, group="guardian"):
    seen = set()
    for r in rules:
        r.validate()
        if r.alert in seen:
            raise RuleError(f"duplicate alert {r.alert}")
        seen.add(r.alert)
    return to_yaml({"groups": [{"name": group, "rules": [
        {"alert": r.alert, "expr": r.expr, "for": r.for_, "labels": {"severity": r.severity},
         "annotations": {"summary": r.summary}} for r in rules]}]})


def alertmanager_config(webhook_url, repeat_interval="1h"):
    """Critical alerts are grouped by alert and robot with a short wait; others are batched.
    webhook_url must be https; the receiver is a placeholder for a real notifier."""
    if not webhook_url.startswith("https://"):
        raise RuleError("webhook_url must be https")
    return to_yaml({
        "route": {
            "receiver": "operators",
            "group_by": ["alertname", "robot"],
            "group_wait": "10s",
            "group_interval": "1m",
            "repeat_interval": repeat_interval,
            "routes": [{"matchers": ['severity="critical"'], "receiver": "operators",
                        "group_wait": "0s", "repeat_interval": "15m"}],
        },
        "receivers": [{"name": "operators", "webhook_configs": [{"url": webhook_url, "send_resolved": True}]}],
        "inhibit_rules": [{"source_matchers": ['alertname="GuardianDown"'],
                           "target_matchers": ['severity="warning"'], "equal": ["robot"]}],
    })
