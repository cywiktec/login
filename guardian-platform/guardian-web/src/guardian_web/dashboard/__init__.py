"""Dashboard view model: data for the page, no HTML. Unknown data is shown as unknown."""

from ..fleet import EMERGENCY, OFFLINE, STALE, FleetRegistry

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def build_dashboard(fleet: FleetRegistry, alerts=()):
    """alerts: iterable of dicts with 'severity', 'message' and optional 'robot'.
    Returns a plain dict ready for JSON/templating."""
    summary = fleet.summary()
    clean = []
    for a in alerts:
        if not isinstance(a, dict):
            continue
        severity = a.get("severity") if a.get("severity") in SEVERITY_ORDER else "critical"
        clean.append({"severity": severity, "message": str(a.get("message", "")),
                      "robot": a.get("robot")})
    clean.sort(key=lambda a: SEVERITY_ORDER[a["severity"]])

    if summary[EMERGENCY]:
        overall = "emergency"
    elif summary[OFFLINE] or any(a["severity"] == "critical" for a in clean):
        overall = "critical"
    elif summary[STALE] or clean:
        overall = "warning"
    elif not sum(summary.values()):
        overall = "unknown"  # an empty fleet is not "all good"
    else:
        overall = "ok"

    return {
        "overall": overall,
        "summary": summary,
        "robots": [
            {"robot_id": r.robot_id, "status": status, "state": r.state,
             "battery_pct": r.battery_pct,
             "last_seen": r.last_seen}
            for r, status in fleet.robots()
        ],
        "alerts": clean,
    }
