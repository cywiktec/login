# guardian-testing

Testy między komponentami i narzędzia do odbioru. Czysty Python, bez zależności. Testy
działają na **symulowanym stosie** (prawdziwy kod voice / ai-engine / safety-layer / backup /
telemetry / monitoring / web + atrapa robota); nie używają `guardian-core`, ROS 2 ani sprzętu.

| Moduł | Zadanie |
|---|---|
| `sat` | SAT (testy odbiorcze na miejscu): `run_sat`, `default_checks(probe)`; wyjątek w teście = porażka |
| `sac` | SAC (kryteria akceptacji): progi mierzalne, brakujący lub niepoprawny pomiar = porażka |
| `integration` | `Stack`: głos → intencja → plan → polityka → router → atrapa robota |
| `load` | `run_load` (wątki, percentyle, błędy) i `violations` z progami |
| `safety` | wyczerpujące kontrole niezmienników polityki i `SafetyFSM`; same wykrywają zepsutą implementację |
| `regression` | porównanie z plikami wzorcowymi (`tests/golden/`); brak wzorca = porażka, nic nie powstaje po cichu |

## Uruchamianie

```
make test                          # dodaje ../*/src do PYTHONPATH
GUARDIAN_UPDATE_GOLDEN=1 make test   # przepisuje pliki wzorcowe — przejrzyj diff przed commitem
```

## Założenia i braki

- **SAT = Site Acceptance Test, SAC = Site Acceptance Criteria** — to moja interpretacja skrótów;
  popraw, jeśli oznaczają co innego. Progi w `DEFAULT_CRITERIA` i `default_checks` (0,5 s, 5 s,
  30 %) są placeholderami do uzgodnienia z klientem.
- `sat` wymaga obiektu `probe` łączącego się z prawdziwym robotem/symulatorem — nie ma go jeszcze.
- Testy obciążeniowe mierzą tylko kod w pamięci; progi czasowe nie są asertowane w testach (flaky).
- Brak testów guardian-core, interfejsów ROS 2/protobuf/OpenAPI i guardian-go2-driver oraz
  mission-manager/navigation w scenariuszach integracyjnych.
- Wynik `integration` zależy od tego, że `FakeRobot` odwzorowuje handlery tak jak docelowy
  guardian-core; to do zweryfikowania po podłączeniu.
