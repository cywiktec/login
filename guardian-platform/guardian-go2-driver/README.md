# guardian-go2-driver

Driver layer for the Unitree Go2 in MISIEK AI Guardian. Pure Python, no
dependencies. **Nothing here has been run on a real robot or the Unitree SDK**:
everything is exercised against `InMemoryTransport`.

| Module | Responsibility |
|---|---|
| `dds_bridge` | `Transport` interface, `InMemoryTransport`, and `DdsBridge` (publish requests, subscribe to state) |
| `telemetry` | Validates raw state into `Telemetry`; malformed messages are counted and dropped; freshness via `max_age` |
| `control` | Velocity limits, finite-value validation, latching emergency stop, and a command deadman (`tick()`) |
| `battery` | `{"percent", "plugged"}` from fresh telemetry; stale data is reported as missing |
| `diagnostics` | Transport, telemetry, telemetry-quality and control checks |
| `ros2_bridge` | Maps driver data to dicts shaped like `guardian-interfaces` messages (no rclpy) |

## Safety behavior

- `Controller.move()` rejects NaN/inf and clamps to `Limits`.
- `tick()` must be called periodically by the owner; it stops the robot if no move
  command arrived within `command_timeout`. Nothing calls it automatically.
- After `emergency_stop()`, `move()` is refused until `release()`; `stop()` is always sent.

## To do before hardware use

- Implement a `Transport` for the real DDS/SDK and confirm the topic names and
  request payloads in `dds_bridge` (the current ones are placeholders).
- Replace the default limits (0.5 / 0.3 m/s, 1.0 rad/s) and 0.5 s timeout with tuned values.
- Add a ROS 2 node using `ros2_bridge`.

```
make test
```
