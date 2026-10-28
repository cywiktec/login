"""2D lidar scan handling: validation, sector minimum distance and obstacle clustering."""

import math
from dataclasses import dataclass


class ScanError(ValueError):
    pass


@dataclass(frozen=True)
class Scan:
    angle_min: float
    angle_increment: float
    ranges: tuple
    range_min: float
    range_max: float
    ts: float


def make_scan(angle_min, angle_increment, ranges, range_min, range_max, ts):
    if not ranges:
        raise ScanError("empty scan")
    if not all(math.isfinite(v) for v in (angle_min, angle_increment, range_min, range_max, ts)):
        raise ScanError("non-finite header value")
    if angle_increment <= 0 or not 0 <= range_min < range_max:
        raise ScanError("bad angle or range limits")
    return Scan(angle_min, angle_increment, tuple(float(r) for r in ranges), range_min, range_max, ts)


def valid_points(scan):
    """(angle, range) for usable readings. NaN/inf/out-of-range are dropped, never treated as clear."""
    return [(scan.angle_min + i * scan.angle_increment, r) for i, r in enumerate(scan.ranges)
            if math.isfinite(r) and scan.range_min <= r <= scan.range_max]


def invalid_fraction(scan):
    return 1 - len(valid_points(scan)) / len(scan.ranges)


def min_distance(scan, angle_from, angle_to, max_invalid=0.5):
    """Closest return in a sector; None when too many readings in the sector are unusable
    (unknown, NOT clear). Callers must treat None as an obstacle."""
    idx = [i for i in range(len(scan.ranges))
           if angle_from <= scan.angle_min + i * scan.angle_increment <= angle_to]
    if not idx:
        return None
    good = [scan.ranges[i] for i in idx
            if math.isfinite(scan.ranges[i]) and scan.range_min <= scan.ranges[i] <= scan.range_max]
    if 1 - len(good) / len(idx) > max_invalid or not good:
        return None
    return min(good)


def clusters(scan, gap=0.3, min_points=3):
    """Groups consecutive valid points closer than `gap` metres into obstacles.
    Returns [{'x','y','size','points'}] in the sensor frame."""
    pts = [(r * math.cos(a), r * math.sin(a)) for a, r in valid_points(scan)]
    groups, cur = [], []
    for p in pts:
        if cur and math.dist(cur[-1], p) > gap:
            groups.append(cur)
            cur = []
        cur.append(p)
    if cur:
        groups.append(cur)
    out = []
    for g in groups:
        if len(g) < min_points:
            continue
        out.append({"x": sum(p[0] for p in g) / len(g), "y": sum(p[1] for p in g) / len(g),
                    "size": math.dist(g[0], g[-1]), "points": len(g)})
    return out
