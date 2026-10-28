"""Gazebo SDF world generator: ground plane, light and geofence walls."""

import math
from xml.etree import ElementTree as ET

WALL_HEIGHT = 1.0
WALL_THICKNESS = 0.1


def _wall(index, p1, p2):
    (x1, y1), (x2, y2) = p1, p2
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        raise ValueError("zero-length wall")
    model = ET.Element("model", name=f"fence_{index}")
    ET.SubElement(model, "static").text = "true"
    ET.SubElement(model, "pose").text = (
        f"{(x1 + x2) / 2:g} {(y1 + y2) / 2:g} {WALL_HEIGHT / 2:g} 0 0 {math.atan2(y2 - y1, x2 - x1):g}")
    link = ET.SubElement(model, "link", name="link")
    size = f"{length:g} {WALL_THICKNESS:g} {WALL_HEIGHT:g}"
    for tag in ("collision", "visual"):
        el = ET.SubElement(link, tag, name=tag)
        box = ET.SubElement(ET.SubElement(el, "geometry"), "box")
        ET.SubElement(box, "size").text = size
    return model


def world(name, polygon):
    if len(polygon) < 3:
        raise ValueError("polygon needs at least 3 vertices")
    sdf = ET.Element("sdf", version="1.9")
    w = ET.SubElement(sdf, "world", name=name)
    sun = ET.SubElement(w, "include")
    ET.SubElement(sun, "uri").text = "model://sun"
    ground = ET.SubElement(w, "include")
    ET.SubElement(ground, "uri").text = "model://ground_plane"
    for i in range(len(polygon)):
        w.append(_wall(i, polygon[i], polygon[(i + 1) % len(polygon)]))
    ET.indent(sdf)
    return '<?xml version="1.0"?>\n' + ET.tostring(sdf, encoding="unicode") + "\n"
