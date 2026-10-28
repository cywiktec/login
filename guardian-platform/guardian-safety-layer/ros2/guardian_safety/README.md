# guardian_safety (ROS 2 Jazzy, ament_python)

Węzły warstwy bezpieczeństwa: `heartbeat_node`, `watchdog_node`, `geofence_node`,
`emergency_stop_node`, `safety_manager`. Logika jest w `guardian_safety/logic.py` (bez rclpy,
testowalna) i korzysta z `guardian_safety_layer` — **trzeba go zainstalować pipem w tym samym
środowisku Pythona**.

## Uruchomienie

```
colcon build --packages-select guardian_safety
ros2 launch guardian_safety guardian_safety.launch.py
make test          # testy logiki, bez ROS
```

## Tematy

Wejścia: `/guardian/heartbeat` (String), `/guardian/emergency_stop` (String),
`/guardian/position` (PointStamped), `/guardian/battery_percent` (Float32).
Wyjścia: `/guardian/safety/{estop_active,watchdog_ok,geofence_ok}` (Bool),
`/guardian/safety/level` (String: NORMAL/WARNING/SAFE_MODE/EMERGENCY_STOP),
`/guardian/safety/state` (String: MONITORING/DEGRADED/FAILSAFE/SAFE_MODE/E_STOP).
Usługi (Trigger): `/guardian/emergency_reset`, `/guardian/safety_reset`.

## Zasady

- Brak/przeterminowanie wejścia = awaria (fail-closed). SAFE_MODE i wyżej są zatrzaskiwane do resetu.
- Reset wyłączony (`allow_reset:=false`), bo brak uwierzytelniania; wymaga zdrowych wejść.
- `polygon` jest wymagany; brak = węzeł się nie uruchomi.
- Węzeł e-stop nie jest wznawiany automatycznie (restart zgubiłby zatrzask).

## Konfiguracja (`config/`)

`emergency_stop`, `emergency_reset` (polityka resetu), `watchdog`, `heartbeat`, `geofence`,
`safety_rules` (progi baterii/timeouty), `safety_manager` — ładowane przez launch; żaden
parametr nie występuje w dwóch plikach (test). `qos_profiles.yaml` to tylko dokumentacja
(profile są w `common.py`). Dodatkowy plik: `params_file:=...` (ładowany ostatni).

## Maszyna stanów (`guardian_safety/state.py`)

`SafetyState`: MONITORING, DEGRADED, FAILSAFE, SAFE_MODE, E_STOP. Settery tylko eskalują
(brak obniżania), E_STOP kończy się tylko przez `reset()` (wymaga `allow_reset`), historia
przejść jest ograniczona. `from_level()` mapuje `SafetyLevel` węzła na stan. Moduł jest podpięty do węzła `safety_manager` (publikuje `/guardian/safety/state` obok `level`).
Znaczenie FAILSAFE (utrata wejścia, wstrzymanie) to moje założenie — do potwierdzenia.

## Założenia i luki (niezweryfikowane)

- **Węzły nigdy nie były uruchomione** — w środowisku nie ma ROS 2; sprawdzono tylko testy logiki i kompilację.
- Sterownik Go2 nie reaguje jeszcze na `/guardian/safety/level`.
- Wszystkie progi i wielokątny geofence (10×10 m) to wartości tymczasowe.
- `heartbeat_node` dowodzi tylko działania ścieżki pub/sub, nie żywotności core/sterownika.
- `maintainer` i `license` (Proprietary) zgodnie z Twoim `package.xml`; `std_srvs` dodane do zależności (używane przez usługi).
- Procedura odbioru: `docs/SAT-SAFE.md` (nie wykonana).
