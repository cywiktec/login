"""Fleet registry: heartbeat-based status, worst-first ordering."""

import math
import re
import time
from dataclasses import dataclass
from typing import Optional

ROBOT_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
ONLINE, STALE, OFFLINE, EMERGENCY = "online", "stale", "offline", "emergency"
_ORDER = {EMERGENCY: 0, OFFLINE: 1, STALE: 2, ONLINE: 3}


@dataclass(frozen=True)
class RobotRecord:
    robot_id: str
    state: str
    battery_pct: Optional[float]
    last_seen: float


class FleetRegistry:
    def __init__(self, stale_after=10.0, offline_after=60.0, clock=time.time):
        if not 0 < stale_after < offline_after:
            raise ValueError("need 0 < stale_after < offline_after")
        self.stale_after = stale_after
        self.offline_after = offline_after
        self._clock = clock
        self._robots = {}

    def heartbeat(self, robot_id, state, battery_pct=None):
        """Returns False for invalid input; the previous record is then left to age out."""
        if not isinstance(robot_id, str) or not ROBOT_ID.match(robot_id) or not isinstance(state, str):
            return False
        if battery_pct is not None:
            if (isinstance(battery_pct, bool) or not isinstance(battery_pct, (int, float))
                    or not math.isfinite(battery_pct) or not 0 <= battery_pct <= 100):
                return False
            battery_pct = float(battery_pct)
        self._robots[robot_id] = RobotRecord(robot_id, state, battery_pct, self._clock())
        return True

    def status(self, robot_id):
        rec = self._robots.get(robot_id)
        if rec is None:
            return OFFLINE
        age = self._clock() - rec.last_seen
        if age > self.offline_after:
            return OFFLINE
        # An emergency stop stays visible until the robot reports otherwise or goes offline.
        if rec.state == "EMERGENCY_STOP":
            return EMERGENCY
        return STALE if age > self.stale_after else ONLINE

    def robots(self):
        """[(record, status)], most urgent first, then by id."""
        items = [(r, self.status(r.robot_id)) for r in self._robots.values()]
        return sorted(items, key=lambda it: (_ORDER[it[1]], it[0].robot_id))

    def summary(self):
        counts = {ONLINE: 0, STALE: 0, OFFLINE: 0, EMERGENCY: 0}
        for _, status in self.robots():
            counts[status] += 1
        return counts

    def remove(self, robot_id):
        return self._robots.pop(robot_id, None) is not None
