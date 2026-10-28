# Interfaces

Single source of truth for contracts shared by all guardian components.

| Directory | Contents |
|---|---|
| `ros2_msgs/` | `GuardianState`, `HealthStatus`, `BatteryStatus` |
| `ros2_srvs/` | `SendCommand`, `TakeSnapshot`, `Recover` |
| `ros2_actions/` | `ExecuteMission` |
| `protobuf/` | `guardian/v1/guardian.proto` (gRPC service + messages) |
| `openapi/` | `guardian.yaml` (REST API, OpenAPI 3.0) |

## Keeping definitions in sync

The state enum exists in four places and must match
`guardian_core.state_manager.GuardianState`: the ROS 2 message, the protobuf enum,
the OpenAPI schema, and the Python enum. Change them together.

Protobuf enum values are offset by one (`STATE_UNSPECIFIED = 0`) from the ROS 2
constants, as proto3 requires a zero default.

## Status

The ROS 2 package files (`package.xml`, `CMakeLists.txt`) have not been built with
colcon. `protobuf/` and `openapi/` are validated with `make validate`.
