"""Routes: ordered waypoints with validation and length."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Waypoint:
    name: str
    x: float
    y: float


class Route:
    def __init__(self, route_id, waypoints):
        if not waypoints:
            raise ValueError("a route needs at least one waypoint")
        names = [w.name for w in waypoints]
        if len(set(names)) != len(names):
            raise ValueError("waypoint names must be unique")
        self.route_id = route_id
        self.waypoints = list(waypoints)

    def length(self):
        return sum(
            math.dist((a.x, a.y), (b.x, b.y))
            for a, b in zip(self.waypoints, self.waypoints[1:])
        )

    def reversed(self, route_id=None):
        return Route(route_id or f"{self.route_id}-reversed", self.waypoints[::-1])


class RouteManager:
    def __init__(self):
        self._routes = {}

    def add(self, route):
        if route.route_id in self._routes:
            raise ValueError(f"route {route.route_id!r} already exists")
        self._routes[route.route_id] = route

    def get(self, route_id):
        try:
            return self._routes[route_id]
        except KeyError:
            raise KeyError(f"unknown route {route_id!r}") from None

    def ids(self):
        return sorted(self._routes)
