"""Object-detector post-processing (YOLO-style): parsing, filtering and NMS.

This does not run a neural network; it consumes raw detections produced by one.
"""

import math
from dataclasses import dataclass


class DetectionError(ValueError):
    pass


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def area(self):
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    @property
    def center(self):
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


def make_detection(label, confidence, x1, y1, x2, y2):
    vals = (confidence, x1, y1, x2, y2)
    if not label or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                            for v in vals):
        raise DetectionError("bad detection values")
    if not 0.0 <= confidence <= 1.0:
        raise DetectionError("confidence outside 0-1")
    if x2 <= x1 or y2 <= y1:
        raise DetectionError("empty or inverted box")
    return Detection(label, float(confidence), float(x1), float(y1), float(x2), float(y2))


def iou(a, b):
    ix = max(0.0, min(a.x2, b.x2) - max(a.x1, b.x1))
    iy = max(0.0, min(a.y2, b.y2) - max(a.y1, b.y1))
    inter = ix * iy
    union = a.area + b.area - inter
    return inter / union if union > 0 else 0.0


def nms(detections, iou_threshold=0.5):
    """Per-label non-maximum suppression, highest confidence kept."""
    kept = []
    for d in sorted(detections, key=lambda d: -d.confidence):
        if all(k.label != d.label or iou(k, d) < iou_threshold for k in kept):
            kept.append(d)
    return kept


def postprocess(raw, labels, min_confidence=0.5, iou_threshold=0.5):
    """raw: iterable of (class_id, confidence, x1, y1, x2, y2). Malformed rows are dropped and counted.
    Returns (detections, dropped)."""
    out, dropped = [], 0
    for row in raw:
        try:
            cid, conf, x1, y1, x2, y2 = row
            if isinstance(cid, bool) or not isinstance(cid, int) or not 0 <= cid < len(labels):
                raise DetectionError("bad class id")
            d = make_detection(labels[cid], conf, x1, y1, x2, y2)
        except (DetectionError, TypeError, ValueError):
            dropped += 1
            continue
        if d.confidence >= min_confidence:
            out.append(d)
    return nms(out, iou_threshold), dropped
