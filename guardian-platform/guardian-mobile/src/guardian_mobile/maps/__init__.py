"""Map view model: world <-> screen conversion and overlays."""

import math


class MapView:
    def __init__(self, min_x, min_y, max_x, max_y, width_px, height_px):
        if not (max_x > min_x and max_y > min_y and width_px > 0 and height_px > 0):
            raise ValueError("invalid map or screen size")
        self.bounds = (min_x, min_y, max_x, max_y)
        self.width_px = width_px
        self.height_px = height_px
        self.geofence = []
        self.route = []

    def to_screen(self, x, y):
        min_x, min_y, max_x, max_y = self.bounds
        px = (x - min_x) / (max_x - min_x) * self.width_px
        py = (1 - (y - min_y) / (max_y - min_y)) * self.height_px  # screen y points down
        return px, py

    def to_world(self, px, py):
        min_x, min_y, max_x, max_y = self.bounds
        return (min_x + px / self.width_px * (max_x - min_x),
                min_y + (1 - py / self.height_px) * (max_y - min_y))

    def contains(self, x, y):
        min_x, min_y, max_x, max_y = self.bounds
        return math.isfinite(x) and math.isfinite(y) and min_x <= x <= max_x and min_y <= y <= max_y

    def set_geofence(self, polygon):
        if len(polygon) < 3:
            raise ValueError("geofence needs at least 3 points")
        self.geofence = list(polygon)

    def set_route(self, waypoints):
        self.route = list(waypoints)

    def geofence_screen(self):
        return [self.to_screen(x, y) for x, y in self.geofence]

    def route_screen(self):
        return [self.to_screen(x, y) for x, y in self.route]

    def inside_geofence(self, x, y):
        """Display-only hint. The robot-side geofence in guardian-safety-layer is the authority."""
        if not self.geofence:
            return True
        inside = False
        j = len(self.geofence) - 1
        for i, (xi, yi) in enumerate(self.geofence):
            xj, yj = self.geofence[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
        return inside
