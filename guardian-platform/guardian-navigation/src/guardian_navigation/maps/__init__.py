"""Occupancy grid with world <-> cell conversion."""

import math


class OccupancyGrid:
    def __init__(self, width, height, resolution=1.0, origin=(0.0, 0.0)):
        if width < 1 or height < 1:
            raise ValueError("grid must be at least 1x1")
        if resolution <= 0:
            raise ValueError("resolution must be positive")
        self.width = width
        self.height = height
        self.resolution = resolution
        self.origin = origin
        self._blocked = [[False] * width for _ in range(height)]

    def in_bounds(self, cx, cy):
        return 0 <= cx < self.width and 0 <= cy < self.height

    def is_free(self, cx, cy):
        """Out-of-bounds cells are never free."""
        return self.in_bounds(cx, cy) and not self._blocked[cy][cx]

    def set_blocked(self, cx, cy, blocked=True):
        if not self.in_bounds(cx, cy):
            raise IndexError(f"cell ({cx}, {cy}) is outside the grid")
        self._blocked[cy][cx] = blocked

    def world_to_cell(self, x, y):
        return (
            math.floor((x - self.origin[0]) / self.resolution),
            math.floor((y - self.origin[1]) / self.resolution),
        )

    def cell_to_world(self, cx, cy):
        """Center of the cell."""
        return (
            self.origin[0] + (cx + 0.5) * self.resolution,
            self.origin[1] + (cy + 0.5) * self.resolution,
        )

    def cells(self):
        for cy in range(self.height):
            for cx in range(self.width):
                yield cx, cy
