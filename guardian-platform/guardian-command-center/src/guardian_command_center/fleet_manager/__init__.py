"""Fleet registry with role-checked command queue. Clock injected; fails closed."""

import math
import time

ROLES = {"viewer": 0, "operator": 1, "admin": 2}
COMMANDS = {"emergency_stop": 0, "return_to_base": 1, "start_patrol": 1, "abort_mission": 1}
# Minimum role level per command. E-stop is open to every known role: it only makes things safer.


class CommandRefused(Exception):
    pass


class FleetManager:
    def __init__(self, stale_after=10.0, clock=time.monotonic):
        self.stale_after = stale_after
        self._clock = clock
        self._robots = {}
        self._queues = {}

    def heartbeat(self, robot_id, state, battery_pct=None, position=None):
        if not robot_id or not state:
            raise ValueError("robot_id and state required")
        if battery_pct is not None and not (math.isfinite(battery_pct) and 0 <= battery_pct <= 100):
            raise ValueError("battery_pct must be 0-100")
        if position is not None and not all(math.isfinite(c) for c in position):
            raise ValueError("position must be finite")
        self._robots[robot_id] = {"state": state, "battery_pct": battery_pct,
                                  "position": tuple(position) if position else None,
                                  "seen": self._clock()}
        self._queues.setdefault(robot_id, [])

    def status(self, robot_id):
        r = self._robots.get(robot_id)
        if r is None:
            return "unknown"
        return "online" if self._clock() - r["seen"] <= self.stale_after else "stale"

    def robots(self):
        return {rid: dict(r, status=self.status(rid)) for rid, r in sorted(self._robots.items())}

    def issue(self, robot_id, command, operator, role):
        if command not in COMMANDS:
            raise CommandRefused(f"unknown command: {command!r}")
        if role not in ROLES:
            raise CommandRefused(f"unknown role: {role!r}")
        if not operator:
            raise CommandRefused("operator required")
        if robot_id not in self._robots:
            raise CommandRefused("unknown robot")
        if ROLES[role] < COMMANDS[command]:
            raise CommandRefused(f"role {role} may not issue {command}")
        if command != "emergency_stop" and self.status(robot_id) != "online":
            raise CommandRefused("robot is not online; only emergency_stop is queued")
        entry = {"command": command, "operator": operator, "at": self._clock()}
        queue = self._queues[robot_id]
        # E-stop goes to the front so it is delivered first.
        queue.insert(0, entry) if command == "emergency_stop" else queue.append(entry)
        return entry

    def estop_all(self, operator, role):
        """Queues an e-stop for every known robot, including stale ones."""
        return [rid for rid in sorted(self._robots) if self.issue(rid, "emergency_stop", operator, role)]

    def next_command(self, robot_id):
        queue = self._queues.get(robot_id)
        return queue.pop(0) if queue else None
