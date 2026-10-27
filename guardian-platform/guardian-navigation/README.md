# guardian-navigation

Navigation for MISIEK AI Guardian: mapping, path planning, waypoint following,
obstacle handling, localization and geofences. Pure Python, no dependencies;
not yet connected to sensors, `guardian-go2-driver` or `guardian-core`.

| Module | Responsibility |
|---|---|
| `maps` | `OccupancyGrid` with world/cell conversion; out-of-bounds is never free |
| `planner` | A* (8-connected, no corner cutting); raises `NoPathError` |
| `waypoint` | `WaypointTracker` advances along a path within a tolerance |
| `obstacle` | `CLEAR`/`SLOW`/`STOP` from range readings; `mark_obstacle` blocks grid cells |
| `localization` | Dead-reckoning `Localizer` with weighted absolute corrections |
| `geofence_provider` | Named polygons (JSON loadable); can block everything outside a fence on a grid |

## Notes

- An empty or entirely invalid range scan classifies as `STOP`, not `CLEAR`.
- `geofence_provider` carries its own point-in-polygon check so this package has no
  dependency on `guardian-safety-layer`; keep the two behaviors (edges inside) aligned.
- The default distances (1.5 m slow, 0.5 m stop) and waypoint tolerance (0.3 m) are
  placeholders until tuned on the robot.

```
make test
```
