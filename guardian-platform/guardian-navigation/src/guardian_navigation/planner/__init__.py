"""A* path planning on an OccupancyGrid (8-connected, no corner cutting)."""

import heapq
import math

_MOVES = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


class NoPathError(RuntimeError):
    pass


class PathPlanner:
    def __init__(self, grid):
        self.grid = grid

    def plan_cells(self, start, goal):
        if not self.grid.is_free(*start):
            raise NoPathError(f"start {start} is not free")
        if not self.grid.is_free(*goal):
            raise NoPathError(f"goal {goal} is not free")

        def h(cell):
            return math.hypot(cell[0] - goal[0], cell[1] - goal[1])

        best = {start: 0.0}
        parent = {}
        heap = [(h(start), 0.0, start)]
        while heap:
            _, g, cell = heapq.heappop(heap)
            if cell == goal:
                return self._rebuild(parent, cell)
            if g > best.get(cell, math.inf):
                continue
            for dx, dy in _MOVES:
                nxt = (cell[0] + dx, cell[1] + dy)
                if not self.grid.is_free(*nxt):
                    continue
                if dx and dy and not (
                    self.grid.is_free(cell[0] + dx, cell[1])
                    and self.grid.is_free(cell[0], cell[1] + dy)
                ):
                    continue
                ng = g + math.hypot(dx, dy)
                if ng < best.get(nxt, math.inf):
                    best[nxt] = ng
                    parent[nxt] = cell
                    heapq.heappush(heap, (ng + h(nxt), ng, nxt))
        raise NoPathError(f"no path from {start} to {goal}")

    def plan(self, start_xy, goal_xy):
        """Plan in world coordinates; returns a list of (x, y) cell centers."""
        cells = self.plan_cells(
            self.grid.world_to_cell(*start_xy), self.grid.world_to_cell(*goal_xy)
        )
        return [self.grid.cell_to_world(*c) for c in cells]

    @staticmethod
    def _rebuild(parent, cell):
        path = [cell]
        while cell in parent:
            cell = parent[cell]
            path.append(cell)
        return path[::-1]
