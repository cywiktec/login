"""Mission plans built from routes."""

from dataclasses import dataclass, field

from ..route_manager import Route


@dataclass
class MissionPlan:
    mission_id: str
    route: Route
    loops: int = 1
    return_to_base: bool = True
    base: str = "base"

    def steps(self):
        """Waypoint names in visiting order, ending at base if requested."""
        names = [w.name for w in self.route.waypoints] * self.loops
        if self.return_to_base and (not names or names[-1] != self.base):
            names.append(self.base)
        return names


class Planner:
    def patrol(self, mission_id, route, loops=1, return_to_base=True, base="base"):
        if loops < 1:
            raise ValueError("loops must be at least 1")
        return MissionPlan(mission_id, route, loops, return_to_base, base)
