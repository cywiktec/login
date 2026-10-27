# guardian-safety-layer

Independent safety supervision for MISIEK AI Guardian. Pure Python, no
dependencies; hardware and ROS 2 wiring are not part of this package yet.

| Module | Responsibility |
|---|---|
| `geofence` | Polygon containment check (edges count as inside) |
| `estop` | Latching emergency stop with trigger listeners |
| `watchdog` | Per-source heartbeat timeouts (injectable clock) |
| `battery_guard` | `OK` / `LOW` / `CRITICAL` / `UNKNOWN` from percent and charging state |
| `failover` | Ordered fallback handlers; reports every failure if all fail |
| `safety_fsm` | `NORMAL` → `WARNING` → `SAFE_MODE` → `EMERGENCY_STOP`; escalate-only, e-stop latched |
| `risk_engine` | Combines the signals above into one `SafetyLevel` |

## Fail-safe choices

- Unknown battery data yields `WARNING`; unknown position (`inside_geofence=None`) yields `SAFE_MODE`.
- A plugged-in battery is never `LOW` or `CRITICAL`.
- `SafetyFSM.reset()` refuses to clear `EMERGENCY_STOP`; use `clear_emergency_stop()`.
  `EmergencyStop.reset()` does no authorization itself, so callers must gate it.

The thresholds (30% low, 15% critical) are placeholders; set them from real robot data.

```
make test
```
