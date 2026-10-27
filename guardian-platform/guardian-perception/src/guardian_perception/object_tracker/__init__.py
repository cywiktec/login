"""Greedy IoU tracker with stable ids and a maximum age for lost tracks."""

from ..yolo import iou


class Track:
    def __init__(self, track_id, det, ts):
        self.id = track_id
        self.det = det
        self.first_ts = ts
        self.last_ts = ts
        self.hits = 1
        self.missed = 0

    @property
    def label(self):
        return self.det.label


class ObjectTracker:
    def __init__(self, iou_threshold=0.3, max_missed=5, min_hits=2):
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self.min_hits = min_hits
        self._tracks = []
        self._next_id = 1

    def update(self, detections, ts):
        """Associates detections (same label only) to tracks, best IoU first."""
        pairs = sorted(((iou(t.det, d), ti, di) for ti, t in enumerate(self._tracks)
                        for di, d in enumerate(detections) if t.label == d.label), reverse=True)
        used_t, used_d = set(), set()
        for score, ti, di in pairs:
            if score < self.iou_threshold:
                break
            if ti in used_t or di in used_d:
                continue
            t = self._tracks[ti]
            t.det, t.last_ts, t.hits, t.missed = detections[di], ts, t.hits + 1, 0
            used_t.add(ti)
            used_d.add(di)
        for ti, t in enumerate(self._tracks):
            if ti not in used_t:
                t.missed += 1
        for di, d in enumerate(detections):
            if di not in used_d:
                self._tracks.append(Track(self._next_id, d, ts))
                self._next_id += 1
        self._tracks = [t for t in self._tracks if t.missed <= self.max_missed]
        return self.confirmed()

    def confirmed(self):
        """Tracks seen at least `min_hits` times and currently matched."""
        return [t for t in self._tracks if t.hits >= self.min_hits and t.missed == 0]

    def all_tracks(self):
        return list(self._tracks)
