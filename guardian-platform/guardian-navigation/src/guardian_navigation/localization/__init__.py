"""Dead-reckoning pose estimate with absolute corrections."""

import math
from dataclasses import dataclass


def normalize_angle(theta):
    return math.atan2(math.sin(theta), math.cos(theta))


@dataclass(frozen=True)
class Pose:
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0


class Localizer:
    def __init__(self, pose=Pose()):
        self._pose = pose

    @property
    def pose(self):
        return self._pose

    def predict(self, v, omega, dt):
        """Integrate forward speed v (m/s) and yaw rate omega (rad/s) over dt seconds."""
        if dt < 0:
            raise ValueError("dt must not be negative")
        p = self._pose
        theta = p.theta + omega * dt
        # Midpoint heading reduces error on turns.
        mid = p.theta + omega * dt / 2
        self._pose = Pose(
            p.x + v * dt * math.cos(mid),
            p.y + v * dt * math.sin(mid),
            normalize_angle(theta),
        )
        return self._pose

    def correct(self, x, y, theta=None, weight=1.0):
        """Blend toward an absolute fix; weight 1.0 replaces the estimate."""
        if not 0 < weight <= 1:
            raise ValueError("weight must be in (0, 1]")
        p = self._pose
        new_theta = p.theta
        if theta is not None:
            new_theta = normalize_angle(p.theta + weight * normalize_angle(theta - p.theta))
        self._pose = Pose(
            p.x + weight * (x - p.x),
            p.y + weight * (y - p.y),
            new_theta,
        )
        return self._pose
