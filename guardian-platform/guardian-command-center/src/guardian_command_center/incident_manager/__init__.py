"""Incident lifecycle: open -> acknowledged -> resolved, with acknowledgement deadlines."""

SEVERITIES = {1: 60.0, 2: 300.0, 3: 900.0, 4: 3600.0}  # severity 1 = most severe; ack deadline in s (placeholders)


class IncidentManager:
    def __init__(self):
        self._incidents = {}
        self._next = 1

    def open(self, robot_id, kind, severity, ts):
        """Re-reporting an unresolved (robot, kind) returns the existing incident (no duplicates);
        a more severe report raises its severity."""
        if severity not in SEVERITIES:
            raise ValueError(f"severity must be one of {sorted(SEVERITIES)}")
        if not robot_id or not kind:
            raise ValueError("robot_id and kind required")
        for inc in self._incidents.values():
            if inc["robot_id"] == robot_id and inc["kind"] == kind and inc["status"] != "resolved":
                inc["severity"] = min(inc["severity"], severity)
                inc["count"] += 1
                return inc["id"]
        inc_id = self._next
        self._next += 1
        self._incidents[inc_id] = {"id": inc_id, "robot_id": robot_id, "kind": kind, "severity": severity,
                                   "status": "open", "opened": ts, "acked": None, "resolved": None,
                                   "ack_by": None, "resolved_by": None, "note": "", "count": 1}
        return inc_id

    def get(self, inc_id):
        return dict(self._incidents[inc_id])

    def ack(self, inc_id, operator, ts):
        inc = self._incidents[inc_id]
        if inc["status"] != "open":
            raise ValueError(f"cannot acknowledge a {inc['status']} incident")
        if not operator:
            raise ValueError("operator required")
        inc.update(status="acknowledged", acked=ts, ack_by=operator)

    def resolve(self, inc_id, operator, ts, note):
        inc = self._incidents[inc_id]
        if inc["status"] != "acknowledged":
            raise ValueError("an incident must be acknowledged before it is resolved")
        if not operator or not note:
            raise ValueError("operator and note required")
        inc.update(status="resolved", resolved=ts, resolved_by=operator, note=note)

    def overdue(self, now):
        """Open incidents past their acknowledgement deadline, most severe first."""
        late = [dict(i) for i in self._incidents.values()
                if i["status"] == "open" and now - i["opened"] > SEVERITIES[i["severity"]]]
        return sorted(late, key=lambda i: (i["severity"], i["opened"]))

    def all(self):
        return [dict(i) for i in self._incidents.values()]
