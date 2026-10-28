"""Person detection on top of detections or confirmed tracks."""

PERSON = "person"


def persons(detections, min_confidence=0.6):
    return [d for d in detections if d.label == PERSON and d.confidence >= min_confidence]


def count(detections, min_confidence=0.6):
    return len(persons(detections, min_confidence))


def nearest_by_box_height(detections, min_confidence=0.6):
    """Taller box = closer (rough proxy; no calibration). None when nobody is detected."""
    ps = persons(detections, min_confidence)
    return max(ps, key=lambda d: d.y2 - d.y1) if ps else None


def in_zone(detection, zone):
    """True if the box centre lies in zone=(x1, y1, x2, y2), image coordinates."""
    cx, cy = detection.center
    return zone[0] <= cx <= zone[2] and zone[1] <= cy <= zone[3]
