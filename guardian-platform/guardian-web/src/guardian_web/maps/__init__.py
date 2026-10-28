"""Versioned map definitions (bounds, geofence, waypoints) with validation.

The robot's own safety layer re-checks everything; this store only refuses nonsense early.
"""

import math
import re

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$")


class MapError(ValueError):
    pass


def _point(p, what):
    if (not isinstance(p, (list, tuple)) or len(p) != 2
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in p)):
        raise MapError(f"{what}: expected [x, y] finite numbers")
    return (float(p[0]), float(p[1]))


def _area(poly):
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                   for i in range(len(poly)))) / 2


def validate_map(definition):
    """Returns a normalized copy or raises MapError."""
    if not isinstance(definition, dict):
        raise MapError("map must be an object")
    b = definition.get("bounds")
    if not isinstance(b, (list, tuple)) or len(b) != 4:
        raise MapError("bounds must be [min_x, min_y, max_x, max_y]")
    min_x, min_y, max_x, max_y = (_point(b[:2], "bounds")[0], _point(b[:2], "bounds")[1],
                                  _point(b[2:], "bounds")[0], _point(b[2:], "bounds")[1])
    if not (max_x > min_x and max_y > min_y):
        raise MapError("bounds are empty")

    def inside(p):
        return min_x <= p[0] <= max_x and min_y <= p[1] <= max_y

    fence = [_point(p, "geofence") for p in definition.get("geofence", [])]
    if len(fence) < 3 or _area(fence) == 0:
        raise MapError("geofence needs a polygon with area")
    if not all(inside(p) for p in fence):
        raise MapError("geofence extends outside the map bounds")
    waypoints = [_point(p, "waypoint") for p in definition.get("waypoints", [])]
    if not all(inside(p) for p in waypoints):
        raise MapError("waypoint outside the map bounds")
    return {"bounds": [min_x, min_y, max_x, max_y], "geofence": fence, "waypoints": waypoints}


class MapStore:
    def __init__(self):
        self._maps = {}  # name -> list of versions

    def save(self, name, definition):
        if not isinstance(name, str) or not NAME.match(name):
            raise MapError("bad map name")
        normalized = validate_map(definition)
        versions = self._maps.setdefault(name, [])
        versions.append(normalized)
        return len(versions)

    def get(self, name, version=None):
        versions = self._maps.get(name)
        if not versions:
            return None
        index = len(versions) if version is None else version
        return versions[index - 1] if 1 <= index <= len(versions) else None

    def names(self):
        return sorted(self._maps)

    def version_count(self, name):
        return len(self._maps.get(name, []))
