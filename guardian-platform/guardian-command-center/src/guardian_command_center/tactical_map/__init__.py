"""Tactical map: robot positions and geofence status as a GeoJSON-like structure.

Coordinates are planar map metres, not WGS84, so this is not valid GeoJSON for GIS tools.
"""


def _inside(polygon, x, y):
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if abs(cross) < 1e-9 and min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2):
            return True
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def build(robots, polygon):
    """robots: output of FleetManager.robots(). Robots without a position are listed with
    position null; they are never shown as 'inside'. Stale robots are flagged."""
    if len(polygon) < 3:
        raise ValueError("polygon needs at least 3 vertices")
    features = [{"type": "Feature", "properties": {"kind": "geofence"},
                 "geometry": {"type": "Polygon", "coordinates": [[list(p) for p in polygon] + [list(polygon[0])]]}}]
    for rid, r in robots.items():
        pos = r.get("position")
        if pos is None:
            geom, inside = None, None
        else:
            geom, inside = {"type": "Point", "coordinates": list(pos)}, _inside(polygon, *pos)
        features.append({"type": "Feature", "geometry": geom,
                         "properties": {"kind": "robot", "id": rid, "state": r["state"],
                                        "status": r["status"], "inside_geofence": inside,
                                        "alert": r["status"] != "online" or inside is False}})
    return {"type": "FeatureCollection", "features": features}


def alerts(collection):
    return sorted(f["properties"]["id"] for f in collection["features"]
                  if f["properties"]["kind"] == "robot" and f["properties"]["alert"])
