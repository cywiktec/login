"""Named geofence polygons for navigation and the safety layer."""

import json


def point_in_polygon(polygon, x, y):
    """Ray casting; points on an edge count as inside."""
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if (
            abs(cross) <= 1e-9
            and min(x1, x2) <= x <= max(x1, x2)
            and min(y1, y2) <= y <= max(y1, y2)
        ):
            return True
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


class GeofenceProvider:
    def __init__(self):
        self._fences = {}

    def add(self, name, polygon):
        if len(polygon) < 3:
            raise ValueError("a geofence needs at least 3 vertices")
        self._fences[name] = [(float(x), float(y)) for x, y in polygon]

    def load(self, text):
        """Load from JSON: {"name": [[x, y], ...], ...}."""
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("geofence JSON must be an object of name -> vertices")
        for name, polygon in data.items():
            self.add(name, polygon)

    def get(self, name):
        try:
            return list(self._fences[name])
        except KeyError:
            raise KeyError(f"unknown geofence {name!r}") from None

    def names(self):
        return sorted(self._fences)

    def contains(self, name, x, y):
        return point_in_polygon(self.get(name), x, y)

    def apply_to_grid(self, grid, name):
        """Block every grid cell whose center is outside the geofence; returns the count."""
        polygon = self.get(name)
        count = 0
        for cx, cy in grid.cells():
            if not point_in_polygon(polygon, *grid.cell_to_world(cx, cy)):
                grid.set_blocked(cx, cy)
                count += 1
        return count
