"""Scenarios: geofence + waypoints + timed events, run against the simulated robot."""

from dataclasses import dataclass, field

from ..simulation import SimRobot, polygon_contains

REACH_RADIUS = 0.1
DT = 0.1


@dataclass(frozen=True)
class Scenario:
    name: str
    polygon: tuple
    start: tuple
    waypoints: tuple
    battery: float = 100.0
    timeout_s: float = 120.0
    events: tuple = field(default_factory=tuple)  # ((t_seconds, "estop"), ...)
    expect: str = "completed"


def validate(s):
    problems = []
    if not s.name:
        problems.append("no name")
    if len(s.polygon) < 3:
        problems.append("polygon needs >= 3 vertices")
        return problems
    if not polygon_contains(s.polygon, *s.start):
        problems.append("start outside geofence")
    if not s.waypoints:
        problems.append("no waypoints")
    problems.extend(f"waypoint {i} outside geofence" for i, w in enumerate(s.waypoints)
                    if not polygon_contains(s.polygon, *w))
    if s.timeout_s <= 0:
        problems.append("timeout must be positive")
    for t, kind in s.events:
        if kind != "estop" or t < 0:
            problems.append(f"bad event {(t, kind)}")
    return problems


def run(s):
    """Returns (outcome, trace). Outcomes: completed, estop, geofence_breach,
    battery_depleted, timeout. Invalid scenarios raise."""
    problems = validate(s)
    if problems:
        raise ValueError("; ".join(problems))
    robot = SimRobot(*s.start, s.polygon, battery=s.battery)
    pending = sorted(s.events)
    trace = [robot.state()]
    index = 0
    while robot.t < s.timeout_s:
        while pending and pending[0][0] <= robot.t:
            pending.pop(0)
            robot.estop()
        robot.step(DT, s.waypoints[index])
        trace.append(robot.state())
        if robot.breach:
            return "geofence_breach", trace
        if robot.estopped:
            return "estop", trace
        if robot.depleted:
            return "battery_depleted", trace
        if abs(robot.x - s.waypoints[index][0]) + abs(robot.y - s.waypoints[index][1]) <= REACH_RADIUS:
            index += 1
            if index == len(s.waypoints):
                return "completed", trace
    return "timeout", trace


def check(s):
    """True when the outcome matches the scenario's expectation."""
    return run(s)[0] == s.expect


SQUARE = ((0, 0), (10, 0), (10, 10), (0, 10))

BUILTIN = (
    Scenario("patrol_ok", SQUARE, (1, 1), ((5, 1), (5, 5))),
    Scenario("estop_midway", SQUARE, (1, 1), ((9, 1),), events=((2.0, "estop"),), expect="estop"),
    Scenario("battery_runs_out", SQUARE, (1, 1), ((9, 9),), battery=1.0, expect="battery_depleted"),
    Scenario("too_slow", SQUARE, (1, 1), ((9, 9),), timeout_s=2.0, expect="timeout"),
)
