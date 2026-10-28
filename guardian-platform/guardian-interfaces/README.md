# guardian-interfaces

Wspólne kontrakty: definicje wiadomości/usług ROS 2, protobuf i OpenAPI. Szczegóły i zasady
synchronizacji: `docs/README.md`.

| Katalog | Zawartość |
|---|---|
| `ros2_msgs/`, `ros2_srvs/`, `ros2_actions/` | `GuardianState`, `HealthStatus`, `BatteryStatus`; `SendCommand`, `TakeSnapshot`, `Recover`; `ExecuteMission` |
| `protobuf/` | `guardian/v1/guardian.proto` (usługa gRPC) |
| `openapi/` | `guardian.yaml` (REST, OpenAPI 3.0) |

Walidacja: `make validate` (wymaga `grpcio-tools` i `openapi-spec-validator`, których nie ma w
`pyproject.toml`). Wynik: proto kompiluje się, OpenAPI jest poprawne.

## Założenia i braki

- Enum stanu istnieje w czterech miejscach (Python, ROS 2, protobuf, OpenAPI) i trzeba go
  zmieniać razem; nic tego automatycznie nie sprawdza.
- Definicji ROS 2 nie zbudowano (brak `colcon`), więc `package.xml`/`CMakeLists.txt` są niezweryfikowane.
- Żaden komponent nie importuje jeszcze tych kontraktów — każdy ma własne typy.
