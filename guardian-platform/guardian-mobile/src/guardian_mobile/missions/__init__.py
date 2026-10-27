"""Mission drafts built on the phone. Validated locally; the robot re-validates."""

import math
from dataclasses import dataclass, field

MAX_WAYPOINTS = 50


class DraftError(ValueError):
    pass


@dataclass
class MissionDraft:
    name: str
    waypoints: list = field(default_factory=list)
    loops: int = 1

    def add_waypoint(self, x, y, map_view=None):
        for v in (x, y):
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise DraftError("waypoint coordinates must be finite numbers")
        if map_view is not None and not map_view.contains(x, y):
            raise DraftError("waypoint is outside the map")
        if map_view is not None and not map_view.inside_geofence(x, y):
            raise DraftError("waypoint is outside the geofence")
        if len(self.waypoints) >= MAX_WAYPOINTS:
            raise DraftError("too many waypoints")
        self.waypoints.append((float(x), float(y)))

    def remove_waypoint(self, index):
        try:
            del self.waypoints[index]
        except IndexError:
            raise DraftError("no such waypoint") from None

    def validate(self):
        if not self.name.strip():
            raise DraftError("mission needs a name")
        if not self.waypoints:
            raise DraftError("mission needs at least one waypoint")
        if isinstance(self.loops, bool) or not isinstance(self.loops, int) or not 1 <= self.loops <= 20:
            raise DraftError("loops must be an integer 1-20")

    def to_payload(self):
        self.validate()
        return {"name": self.name.strip(), "waypoints": [list(p) for p in self.waypoints],
                "loops": self.loops}


class MissionLibrary:
    def __init__(self):
        self._drafts = {}

    def save(self, draft):
        draft.validate()
        self._drafts[draft.name.strip()] = draft

    def get(self, name):
        return self._drafts.get(name)

    def names(self):
        return sorted(self._drafts)

    def delete(self, name):
        return self._drafts.pop(name, None) is not None
