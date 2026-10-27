"""Mission overview: per-robot mission states and stuck-mission detection."""

STATES = ("pending", "active", "done", "aborted")
_NEXT = {"pending": {"active", "aborted"}, "active": {"done", "aborted"}, "done": set(), "aborted": set()}


class MissionOverview:
    def __init__(self, max_active_s=3600.0):
        self.max_active_s = max_active_s  # placeholder
        self._m = {}

    def create(self, mission_id, robot_id, ts):
        if mission_id in self._m:
            raise ValueError("duplicate mission id")
        if not robot_id:
            raise ValueError("robot_id required")
        self._m[mission_id] = {"id": mission_id, "robot_id": robot_id, "state": "pending",
                               "created": ts, "started": None, "ended": None}

    def move(self, mission_id, state, ts):
        m = self._m[mission_id]
        if state not in _NEXT[m["state"]]:
            raise ValueError(f"{m['state']} -> {state} not allowed")
        if m["state"] == "pending" and state == "active":
            # One active mission per robot.
            if any(o["robot_id"] == m["robot_id"] and o["state"] == "active" for o in self._m.values()):
                raise ValueError("robot already has an active mission")
            m["started"] = ts
        if state in ("done", "aborted"):
            m["ended"] = ts
        m["state"] = state

    def counts(self):
        out = {s: 0 for s in STATES}
        for m in self._m.values():
            out[m["state"]] += 1
        return out

    def stuck(self, now):
        return sorted(m["id"] for m in self._m.values()
                      if m["state"] == "active" and now - m["started"] > self.max_active_s)

    def by_robot(self, robot_id):
        return [dict(m) for m in self._m.values() if m["robot_id"] == robot_id]
