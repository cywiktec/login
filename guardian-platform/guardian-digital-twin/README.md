# guardian-digital-twin

Symulacja offline do testowania misji. Czysty Python; `make test` (14 testów). To **uproszczony
model punktowy 2D**, nie fizyka robota.

| Moduł | Zadanie |
|---|---|
| `simulation` | `SimRobot`: kinematyka z limitem prędkości, bateria, geofence (wyjście poza strefę = odmowa ruchu + zatrzymanie awaryjne, zatrzaskiwane), e-stop |
| `scenarios` | `Scenario` (strefa, punkty, zdarzenia, oczekiwany wynik), `validate`, `run`, `check`; 4 scenariusze wbudowane |
| `replay` | zapis/odczyt śladu JSONL (atomowy zapis, uszkodzony ślad = `TraceError`), `replay`, `diff` |
| `gazebo` | generator świata SDF (podłoże + ściany geofence) |
| `rviz` | markery (geofence, punkty trasy) jako słowniki i minimalny plik `.rviz` |

Symulacja jest deterministyczna (stały krok 0,1 s), więc ślady można porównywać w testach regresji.

## Założenia i braki

- Zużycie baterii (0,5 %/m) i prędkość 1 m/s to placeholdery, nie dane Go2.
- SDF i konfiguracja RViz **nie były uruchomione** w Gazebo/RViz (brak tych narzędzi); sprawdzono
  tylko poprawność XML. Nazwy wtyczek RViz i modeli (`model://sun`) mogą wymagać poprawek.
- Test punkt-w-wielokącie jest kolejną kopią (jak w safety-layer, navigation, mobile, web).
- Brak połączenia ze `guardian-core` — to osobny model, nie podstawa dla prawdziwego sterownika.
- Zdarzenia scenariuszy: tylko `estop`; brak utraty telemetrii, przeszkód i opóźnień.
