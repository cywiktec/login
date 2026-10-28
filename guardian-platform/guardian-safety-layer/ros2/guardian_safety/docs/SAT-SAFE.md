# SAT-SAFE — test akceptacyjny pakietu guardian_safety

**ID:** SAT-001
**Wersja:** 1.0
**Status:** szkic
**Właściciel:** do ustalenia
**Data:** 2026-10-27

## Cel

Potwierdzić na działającym ROS 2 Jazzy, że węzły `guardian_safety` realizują zachowania
bezpieczeństwa. **Żaden krok nie był jeszcze wykonany** (w środowisku autora nie ma ROS 2);
kolumna „Wynik” jest pusta celowo.

## Zakres

Węzły: `heartbeat_node`, `watchdog_node`, `geofence_node`, `emergency_stop_node`,
`safety_manager`. Poza zakresem: sterownik Go2 (jeszcze nie czyta `/guardian/safety/level`).

## Przygotowanie

```
colcon build --packages-select guardian_safety && source install/setup.bash
pip install guardian-safety-layer   # to samo środowisko Pythona
ros2 launch guardian_safety guardian_safety.launch.py
```

Pomocniczo (publikowanie wejść, co ~0,2 s):
`ros2 topic pub -r 5 /guardian/position geometry_msgs/msg/PointStamped "{point: {x: 5.0, y: 5.0}}"`
oraz `ros2 topic pub -r 1 /guardian/battery_percent std_msgs/msg/Float32 "{data: 80.0}"`.

## Kroki

| Krok | Działanie | Oczekiwany wynik | Wynik |
|------|-----------|------------------|-------|
| SAT-SAFE-01 | Uruchom launch bez pozycji i baterii; `ros2 topic echo /guardian/safety/level` | SAFE_MODE (brak wejść), bez zatrzaśnięcia w oknie `startup_grace_s` | |
| SAT-SAFE-02 | Opublikuj pozycję (5,5) i baterię 80 | NORMAL | |
| SAT-SAFE-03 | Zatrzymaj `heartbeat_node` | `watchdog_ok` = false po ~1 s; poziom SAFE_MODE i **pozostaje** po wznowieniu heartbeatu | |
| SAT-SAFE-04 | Opublikuj pozycję (50,5) | `geofence_ok` = false; SAFE_MODE | |
| SAT-SAFE-05 | Przerwij publikowanie pozycji >1 s | `geofence_ok` = false (stale); SAFE_MODE | |
| SAT-SAFE-06 | Bateria 20, potem 10 | WARNING, potem SAFE_MODE | |
| SAT-SAFE-07 | `ros2 topic pub --once /guardian/emergency_stop std_msgs/msg/String "{data: test}"`; zmierz czas do EMERGENCY_STOP | EMERGENCY_STOP, czas ≤ 0,5 s (wartość tymczasowa) | |
| SAT-SAFE-08 | Wywołaj `/guardian/emergency_reset` i `/guardian/safety_reset` bez `allow_reset` | oba `success=false`; poziom bez zmian | |
| SAT-SAFE-09 | Uruchom z `allow_reset:=true` w obu węzłach; wywołaj `emergency_reset`, potem `safety_reset` przy zdrowych wejściach | `success=true`; NORMAL. `safety_reset` przy złych wejściach → `success=false` | |
| SAT-SAFE-10 | Zabij `watchdog_node` | po >1 s SAFE_MODE (brak statusu = awaria) | |
| SAT-SAFE-11 | Zabij `emergency_stop_node` | po >1 s co najmniej SAFE_MODE; węzeł nie jest automatycznie wznawiany | |

## Kryteria akceptacji

Podpis tylko gdy **wszystkie** kroki mają wynik PASS. Każdy FAIL lub pusty wynik = brak
akceptacji. Wyniki: data, wykonawca, wersja pakietu.

## Założenia i ograniczenia

- Limity czasu i progi baterii są wartościami tymczasowymi.
- Heartbeat `safety_stack` nie dowodzi żywotności `guardian_core` ani sterownika.
- Reset jest wyłączony domyślnie, bo brak uwierzytelniania.

## Historia zmian

| Wersja | Data | Zmiana |
|--------|------|--------|
| 1.0 | 2026-10-27 | Szkic, nie wykonany |
