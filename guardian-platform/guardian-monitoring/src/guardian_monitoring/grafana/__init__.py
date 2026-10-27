"""Grafana dashboard JSON and provisioning files generated from dashboard specs."""

import json

from ..dashboards import Dashboard
from ..yamlout import to_yaml

SCHEMA_VERSION = 39  # assumption: recent Grafana; Grafana migrates older schemas on import


def _panel(panel, index, datasource_uid):
    steps = [{"color": color, "value": None if i == 0 else value}
             for i, (value, color) in enumerate(panel.thresholds)] or [{"color": "green", "value": None}]
    defaults = {"unit": panel.unit, "thresholds": {"mode": "absolute", "steps": steps}}
    if panel.min is not None:
        defaults["min"] = panel.min
    if panel.max is not None:
        defaults["max"] = panel.max
    return {
        "id": index + 1,
        "title": panel.title,
        "type": panel.kind,
        "datasource": {"type": "prometheus", "uid": datasource_uid},
        "targets": [{"expr": panel.expr, "refId": "A", "legendFormat": "{{robot}}"}],
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "gridPos": {"h": 6, "w": 6, "x": (index % 4) * 6, "y": (index // 4) * 6},
    }


def dashboard_json(dashboard: Dashboard, datasource_uid="prometheus"):
    return json.dumps({
        "uid": dashboard.uid,
        "title": dashboard.title,
        "schemaVersion": SCHEMA_VERSION,
        "version": 1,
        "refresh": "10s",
        "time": {"from": "now-1h", "to": "now"},
        "panels": [_panel(p, i, datasource_uid) for i, p in enumerate(dashboard.panels)],
    }, indent=2, sort_keys=True)


def datasource_provisioning(url="http://prometheus:9090", uid="prometheus"):
    return to_yaml({"apiVersion": 1, "datasources": [
        {"name": "Prometheus", "uid": uid, "type": "prometheus", "access": "proxy",
         "url": url, "isDefault": True}]})


def dashboard_provisioning(path="/var/lib/grafana/dashboards"):
    return to_yaml({"apiVersion": 1, "providers": [
        {"name": "guardian", "type": "file", "disableDeletion": False,
         "options": {"path": path}}]})
