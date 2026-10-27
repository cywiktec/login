"""Event detection: person in zone, motion (matches the 'detect_motion' intent) and close obstacle.

Events fire on rising edges only and re-arm after the condition clears, so one situation
produces one event, not one per frame. Unknown input (no data) never clears an active condition.
"""

import math

from ..person_detection import in_zone


class EventDetector:
    def __init__(self, zone, motion_threshold=0.05, obstacle_distance=0.8):
        self.zone = zone
        self.motion_threshold = motion_threshold
        self.obstacle_distance = obstacle_distance
        self._active = set()
        self._last_centres = {}

    def _edge(self, name, condition, ts, **info):
        """condition: True/False, or None for unknown (state is kept)."""
        if condition is None:
            return None
        if condition and name not in self._active:
            self._active.add(name)
            return {"event": name, "ts": ts, **info}
        if not condition:
            self._active.discard(name)
        return None

    def update(self, ts, tracks=None, nearest_obstacle=None):
        """tracks: confirmed tracks (or None if the camera is unavailable);
        nearest_obstacle: metres, or None if the lidar is unavailable."""
        events = []
        if tracks is None:
            person_in_zone = moving = None
        else:
            person_in_zone = any(in_zone(t.det, self.zone) for t in tracks if t.label == "person")
            moving = self._motion(tracks)
        close = None if nearest_obstacle is None or not math.isfinite(nearest_obstacle) \
            else nearest_obstacle < self.obstacle_distance
        for ev in (self._edge("person_in_zone", person_in_zone, ts),
                   self._edge("motion", moving, ts),
                   self._edge("obstacle_close", close, ts, distance=nearest_obstacle)):
            if ev:
                events.append(ev)
        return events

    def _motion(self, tracks):
        moved = False
        centres = {}
        for t in tracks:
            c = t.det.center
            height = max(t.det.y2 - t.det.y1, 1e-9)
            prev = self._last_centres.get(t.id)
            if prev is not None and math.dist(prev, c) / height > self.motion_threshold:
                moved = True
            centres[t.id] = c
        self._last_centres = centres
        return moved
