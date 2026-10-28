"""Obstacle classification from range readings and grid marking."""

import math
from enum import Enum


class ObstacleLevel(Enum):
    CLEAR = "CLEAR"
    SLOW = "SLOW"
    STOP = "STOP"


class ObstacleMonitor:
    def __init__(self, slow_distance=1.5, stop_distance=0.5):
        if not 0 < stop_distance < slow_distance:
            raise ValueError("require 0 < stop_distance < slow_distance")
        self.slow_distance = slow_distance
        self.stop_distance = stop_distance

    def classify(self, ranges):
        """Classify by the nearest valid range (meters).

        Invalid readings (NaN, infinite, negative) are ignored; a scan with no
        valid readings is STOP, because the sensor cannot be trusted.
        """
        valid = [r for r in ranges if math.isfinite(r) and r >= 0]
        if not valid:
            return ObstacleLevel.STOP
        nearest = min(valid)
        if nearest <= self.stop_distance:
            return ObstacleLevel.STOP
        if nearest <= self.slow_distance:
            return ObstacleLevel.SLOW
        return ObstacleLevel.CLEAR


def mark_obstacle(grid, x, y, radius=0.0):
    """Block every cell whose center lies within radius of (x, y); returns the count."""
    cx, cy = grid.world_to_cell(x, y)
    reach = int(math.ceil(radius / grid.resolution)) + 1
    count = 0
    for gx in range(cx - reach, cx + reach + 1):
        for gy in range(cy - reach, cy + reach + 1):
            if not grid.in_bounds(gx, gy):
                continue
            wx, wy = grid.cell_to_world(gx, gy)
            if (gx, gy) == (cx, cy) or math.hypot(wx - x, wy - y) <= radius:
                grid.set_blocked(gx, gy)
                count += 1
    return count
