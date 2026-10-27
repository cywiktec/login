"""RViz helpers: marker messages (as dicts) for geofence/waypoints and a minimal .rviz config."""

from ..yamlout import to_yaml

FRAME = "map"


def geofence_marker(polygon, marker_id=0):
    if len(polygon) < 3:
        raise ValueError("polygon needs at least 3 vertices")
    pts = list(polygon) + [polygon[0]]
    return {
        "header": {"frame_id": FRAME},
        "ns": "geofence", "id": marker_id,
        "type": 4,  # LINE_STRIP
        "action": 0,
        "scale": {"x": 0.05},
        "color": {"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0},
        "points": [{"x": float(x), "y": float(y), "z": 0.0} for x, y in pts],
    }


def waypoint_markers(waypoints):
    return [{"header": {"frame_id": FRAME}, "ns": "waypoints", "id": i, "type": 2,  # SPHERE
             "action": 0, "pose": {"x": float(x), "y": float(y), "z": 0.0},
             "scale": {"x": 0.2, "y": 0.2, "z": 0.2},
             "color": {"r": 0.0, "g": 1.0, "b": 0.0, "a": 1.0}}
            for i, (x, y) in enumerate(waypoints)]


def config(marker_topic="/guardian/markers"):
    """Minimal RViz2 display config; not loaded in RViz by me, structure follows the usual format."""
    return to_yaml({
        "Visualization Manager": {
            "Global Options": {"Fixed Frame": FRAME},
            "Displays": [
                {"Class": "rviz_default_plugins/Grid", "Name": "Grid", "Enabled": True},
                {"Class": "rviz_default_plugins/Marker", "Name": "Guardian",
                 "Enabled": True, "Topic": {"Value": marker_topic}},
            ],
        }
    })
