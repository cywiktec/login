"""Prometheus text exposition format and scrape config generation."""

import math
import re
from dataclasses import dataclass, field

from ..yamlout import to_yaml

NAME = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
LABEL = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
TYPES = {"gauge", "counter"}


class MetricError(ValueError):
    pass


@dataclass
class Metric:
    name: str
    help: str
    type: str = "gauge"
    samples: list = field(default_factory=list)  # [(labels dict, value)]

    def add(self, value, **labels):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise MetricError(f"{self.name}: value must be a finite number")
        for key in labels:
            if not LABEL.match(key) or key.startswith("__"):
                raise MetricError(f"bad label name {key!r}")
        self.samples.append((labels, value))
        return self


def _escape_label(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _escape_help(text):
    return str(text).replace("\\", "\\\\").replace("\n", "\\n")


def render_metrics(metrics):
    out = []
    for m in metrics:
        if not NAME.match(m.name):
            raise MetricError(f"bad metric name {m.name!r}")
        if m.type not in TYPES:
            raise MetricError(f"bad metric type {m.type!r}")
        out.append(f"# HELP {m.name} {_escape_help(m.help)}")
        out.append(f"# TYPE {m.name} {m.type}")
        for labels, value in m.samples:
            if labels:
                inner = ",".join(f'{k}="{_escape_label(v)}"' for k, v in sorted(labels.items()))
                out.append(f"{m.name}{{{inner}}} {value}")
            else:
                out.append(f"{m.name} {value}")
    return "\n".join(out) + "\n"


def scrape_config(jobs, interval="15s", rule_files=("alerts.yml",), alertmanagers=("alertmanager:9093",)):
    """jobs: {job_name: [host:port, ...]} -> prometheus.yml text."""
    for name, targets in jobs.items():
        if not NAME.match(name.replace("-", "_")) or not targets:
            raise MetricError(f"bad job {name!r}")
    config = {
        "global": {"scrape_interval": interval, "evaluation_interval": interval},
        "rule_files": list(rule_files),
        "alerting": {"alertmanagers": [{"static_configs": [{"targets": list(alertmanagers)}]}]},
        "scrape_configs": [{"job_name": n, "static_configs": [{"targets": list(t)}]}
                           for n, t in sorted(jobs.items())],
    }
    return to_yaml(config)
