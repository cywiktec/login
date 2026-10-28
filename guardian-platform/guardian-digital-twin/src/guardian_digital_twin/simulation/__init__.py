"""Deterministic 2D point-robot simulation (no physics engine): kinematics, battery, geofence, e-stop."""

import math

from dataclasses import dataclass


def polygon_contains(polygon, x, y):
    """Ray casting; boundary points count as inside."""
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if abs(cross) < 1e-9 and min(x1, x2) - 1e-9 <= x <= max(x1, x2) + 1e-9 \
                and min(y1, y2) - 1e-9 <= y <= max(y1, y2) + 1e-9:
            return True
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


@dataclass
class SimConfig:
    max_speed: float = 1.0          # m/s
    battery_per_m: float = 0.5      # percent per metre (placeholder, not Go2 data)


class SimRobot:
    def __init__(self, x, y, polygon, battery=100.0, config=None):
        if len(polygon) < 3:
            raise ValueError("polygon needs at least 3 vertices")
        self.polygon = [(float(a), float(b)) for a, b in polygon]
        if not polygon_contains(self.polygon, x, y):
            raise ValueError("start position outside geofence")
        self.x, self.y, self.battery = float(x), float(y), float(battery)
        self.config = config or SimConfig()
        self.estopped = False
        self.breach = False
        self.t = 0.0

    def estop(self):
        self.estopped = True

    @property
    def depleted(self):
        return self.battery <= 0.0

    def step(self, dt, target):
        """Moves towards target for dt seconds. A move that would leave the geofence is
        refused and latches an e-stop."""
        if not (isinstance(dt, (int, float)) and math.isfinite(dt) and dt > 0):
            raise ValueError("dt must be a positive finite number")
        tx, ty = target
        if not (math.isfinite(tx) and math.isfinite(ty)):
            raise ValueError("target must be finite")
        self.t += dt
        if self.estopped or self.depleted:
            return
        dist = math.hypot(tx - self.x, ty - self.y)
        move = min(dist, self.config.max_speed * dt)
        if move == 0:
            return
        nx = self.x + (tx - self.x) / dist * move
        ny = self.y + (ty - self.y) / dist * move
        if not polygon_contains(self.polygon, nx, ny):
            self.breach = True
            self.estopped = True
            return
        self.x, self.y = nx, ny
        self.battery = max(0.0, self.battery - move * self.config.battery_per_m)

    def state(self):
        return {"t": round(self.t, 6), "x": round(self.x, 6), "y": round(self.y, 6),
                "battery": round(self.battery, 6), "estopped": self.estopped}
