"""Follow a path waypoint by waypoint."""

import math


class WaypointTracker:
    def __init__(self, waypoints, tolerance=0.3):
        if tolerance <= 0:
            raise ValueError("tolerance must be positive")
        self.waypoints = list(waypoints)
        self.tolerance = tolerance
        self._index = 0

    @property
    def done(self):
        return self._index >= len(self.waypoints)

    @property
    def index(self):
        return self._index

    @property
    def current(self):
        return None if self.done else self.waypoints[self._index]

    def update(self, x, y):
        """Advance past every waypoint already within tolerance; return the target."""
        while not self.done and math.dist((x, y), self.current) <= self.tolerance:
            self._index += 1
        return self.current

    def remaining(self):
        return self.waypoints[self._index:]

    def reset(self, index=0):
        if not 0 <= index <= len(self.waypoints):
            raise IndexError("index out of range")
        self._index = index
