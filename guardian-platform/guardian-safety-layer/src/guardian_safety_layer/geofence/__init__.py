"""Polygon geofence (planar x/y coordinates)."""


class Geofence:
    def __init__(self, polygon):
        if len(polygon) < 3:
            raise ValueError("a geofence needs at least 3 vertices")
        self.polygon = [(float(x), float(y)) for x, y in polygon]

    def contains(self, x, y):
        """Ray casting; points exactly on an edge count as inside."""
        inside = False
        n = len(self.polygon)
        for i in range(n):
            x1, y1 = self.polygon[i]
            x2, y2 = self.polygon[(i + 1) % n]
            if self._on_segment(x, y, x1, y1, x2, y2):
                return True
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                inside = not inside
        return inside

    @staticmethod
    def _on_segment(px, py, x1, y1, x2, y2):
        cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
        if abs(cross) > 1e-9:
            return False
        return min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2)
