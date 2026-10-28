# FMEA v2.0 — analiza rodzajów i skutków błędów

**ID:** FMEA-001
**Wersja:** 2.0
**Status:** szkic
**Właściciel:** do ustalenia
**Data:** 2026-10-27

> Dokument generowany z `guardian_docs/fmea/v2.py` (`python -m guardian_docs.build`).
> Nie edytuj ręcznie — zmień dane i wygeneruj ponownie.

## Cel

Wskazać rodzaje błędów komponentów Guardian, ich skutki, zastosowane środki zaradcze i dowody ich
weryfikacji, tak aby było widać luki, a nie tylko pokrycie.

## Zakres

Komponenty monorepo `guardian-platform` (stan kodu z daty dokumentu). Nie obejmuje sprzętu
Unitree Go2, sieci, ani procesu produkcyjnego.

## Metoda

RPN = S × O × D (każde 1–10; D=10 oznacza praktycznie niewykrywalny).
Wymaga działania: RPN ≥ 100 **lub** S ≥ 9. Kolumna „Verified by” wskazuje test w repozytorium;
`-` oznacza brak dowodu (luka).

## Podsumowanie
- Rodzajów błędów: 36; wymagających działania: 21.
- Wymagających działania **bez dowodu weryfikacji (luki): 6**.
- Wg komponentu: ai-engine (3), backup (3), command-center (2), core (3), devops (2), go2-driver (3), installer (2), interfaces (1), mission-manager (1), monitoring (2), navigation (1), perception (4), safety-layer (4), telemetry (2), voice (2), web (1).

## Tabela

| ID | Component | Failure mode | Effect | S | O | D | RPN | Action | Mitigation | Verified by |
|---|---|---|---|---|---|---|---|---|---|---|
| F-015 | perception | Person not detected | No person-in-zone event | 8 | 4 | 7 | 224 | YES | None in software: depends on the (external) model; thresholds untuned | - |
| F-009 | voice | Noise suppresses the spoken 'stop' | E-stop not recognised | 9 | 4 | 6 | 216 | YES | No technical mitigation beyond bare-stop path; physical e-stop button required (not in software) | - |
| F-036 | interfaces | State enum drifts between Python/ROS/protobuf/OpenAPI | Components disagree on state | 7 | 5 | 6 | 210 | YES | Documented rule only; no automatic check | - |
| F-028 | monitoring | Alert rules wrong or never loaded | No alert on a real fault | 8 | 4 | 6 | 192 | YES | Rules generated from code; NOT validated with promtool/amtool | - |
| F-030 | command-center | Queued e-stop lost on restart | E-stop not delivered | 10 | 3 | 6 | 180 | YES | None: queue is in memory | - |
| F-008 | voice | Speech misrecognised as a command | Unintended command | 7 | 5 | 5 | 175 | YES | Wake word required; STT confidence >= 0.6; NaN confidence rejected; bare 'stop' only for e-stop | guardian-voice tests |
| F-004 | safety-layer | Heartbeat/watchdog stops being evaluated | Hung control loop goes unnoticed | 9 | 3 | 6 | 162 | YES | Per-source expiry: a silent heartbeat source expires | guardian-safety-layer watchdog test_expiry_per_source |
| F-005 | ai-engine | LLM misreads intent | Wrong actuating command executed | 8 | 5 | 4 | 160 | YES | LLM actuating intents need confidence >= 0.8; policy by state and source | guardian-ai-engine policy tests |
| F-032 | devops | Secret committed to the repository | Credential leak | 8 | 4 | 5 | 160 | YES | Heuristic secret scanner; env refs only in compose | guardian-devops tests |
| F-003 | safety-layer | Geofence polygon wrong or too permissive | Robot leaves the allowed area | 9 | 3 | 5 | 135 | YES | Polygon validated (>= 3 vertices); boundary counts as inside; simulation latches e-stop on breach | guardian-safety-layer test_inside_outside_and_edge; guardian-digital-twin scenarios |
| F-016 | perception | Tracker swaps identities | Wrong object history | 4 | 5 | 6 | 120 | YES | IoU association with same-label constraint | guardian-perception tracker tests |
| F-035 | installer | ROS repository key not pinned | Supply-chain compromise | 8 | 2 | 7 | 112 | YES | None: key fetched over HTTPS without fingerprint pinning | - |
| F-013 | perception | Lidar returns NaN/inf for a sector | Obstacle treated as free space | 9 | 4 | 3 | 108 | YES | min_distance returns None (unknown) when too many readings are unusable; callers must treat as obstacle | guardian-perception lidar tests |
| F-012 | go2-driver | Battery reading wrong | Mission started on a dying battery | 7 | 3 | 5 | 105 | YES | Battery guard levels and threshold validation | guardian-safety-layer test_levels, test_invalid_thresholds |
| F-010 | go2-driver | Telemetry stops or ages | Decisions on stale state | 8 | 4 | 3 | 96 | no | latest(max_age) returns nothing when stale; consumers fail closed | guardian-go2-driver tests |
| F-020 | core | Recovery reports READY while unhealthy | False sense of recovery | 8 | 3 | 4 | 96 | no | success requires health score >= 80; NaN rejected; health check injectable | guardian-core test_recovery_engine |
| F-027 | monitoring | Stale data exported as healthy | Operators see a green dashboard | 8 | 3 | 4 | 96 | no | guardian_up = 0 when data is stale | guardian-monitoring tests |
| F-033 | devops | Tampered release artifact | Malicious code deployed | 9 | 2 | 5 | 90 | YES | SHA-256 manifest verified before use; no signing | guardian-devops tests |
| F-026 | telemetry | Broker down | No telemetry to the operators | 7 | 4 | 3 | 84 | no | Monitoring alerts on missing data; in-memory broker only - no real transport | - |
| F-006 | ai-engine | Untrusted source issues a command | Unauthorised actuation | 9 | 3 | 3 | 81 | YES | Sources 'none' and 'web' are denied everything except emergency_stop | guardian-ai-engine policy tests |
| F-019 | core | Corrupt snapshot used for recovery | Robot resumes in a wrong state | 9 | 3 | 3 | 81 | YES | RecoveryEngine verifies schema and SHA-256; falls back to older snapshot; FAILED if none | guardian-core test_recovery_engine |
| F-029 | command-center | Command issued by an unauthorised role | Unauthorised actuation | 9 | 3 | 3 | 81 | YES | Role check per command; unknown role refused; no authentication exists yet | guardian-command-center tests |
| F-001 | safety-layer | E-stop command not delivered | Robot keeps moving | 10 | 2 | 4 | 80 | YES | E-stop allowed from every source and state; latched until explicit reset | guardian-safety-layer test_latches_and_notifies_once; guardian-testing safety invariants |
| F-025 | telemetry | Slow client blocks the hub | Telemetry delay for all clients | 5 | 4 | 4 | 80 | no | Bounded per-client queues | guardian-telemetry tests |
| F-014 | perception | Camera frame stale | Detections from the past | 6 | 4 | 3 | 72 | no | CameraSource.latest() returns None when stale | guardian-perception camera tests |
| F-017 | mission-manager | Mission interrupted by power loss | Mission cannot resume | 6 | 4 | 3 | 72 | no | Checkpoint manager and recovery | guardian-mission-manager test_interrupted_and_resume |
| F-018 | navigation | Waypoint outside geofence | Route leaves the allowed area | 8 | 3 | 3 | 72 | no | Map geofence applied to the planning grid, so the planner is confined | guardian-navigation test_apply_to_grid_confines_planner |
| F-007 | ai-engine | Unknown state while evaluating policy | Command allowed in an unknown situation | 8 | 2 | 4 | 64 | no | Unknown state denies all non-read-only intents | guardian-ai-engine policy tests |
| F-021 | core | Journal entry corrupt during replay | Partial replay hides lost actions | 7 | 3 | 3 | 63 | no | Any corrupt entry fails the whole recovery | guardian-core test_recovery_engine |
| F-002 | safety-layer | FSM leaves EMERGENCY_STOP without operator action | Robot restarts motion | 10 | 2 | 3 | 60 | YES | reset() raises at EMERGENCY_STOP; only clear_emergency_stop() leaves it | guardian-testing safety (FSM invariants) |
| F-011 | go2-driver | Malformed telemetry frame | Garbage values enter the system | 7 | 4 | 2 | 56 | no | parse_state rejects non-finite and missing fields | guardian-go2-driver tests |
| F-031 | web | Report injection (HTML/CSV formulas) | Operator browser/spreadsheet compromised | 6 | 3 | 3 | 54 | no | HTML escaped; CSV formula guard | guardian-web tests |
| F-034 | installer | Installer changes the system unexpectedly | Broken host | 6 | 3 | 3 | 54 | no | Dry run by default; preflight; resumable with rollback | guardian-installer tests |
| F-023 | backup | Journal tail torn or tampered | Corrupt history trusted | 6 | 3 | 2 | 36 | no | Hash chain; torn tail detected and truncated | guardian-backup tests |
| F-024 | backup | Retention deletes the only valid snapshot | No recovery possible | 9 | 2 | 2 | 36 | YES | Never deletes the newest valid snapshot | guardian-backup tests |
| F-022 | backup | Snapshot torn on power loss | Lost resume point | 5 | 3 | 2 | 30 | no | Atomic write (temp, fsync, rename, fsync dir) + hash verify | guardian-backup tests |

## Luki

Rodzaje błędów wymagające działania, dla których nie ma testu:

- **F-009** (voice): Noise suppresses the spoken 'stop' — No technical mitigation beyond bare-stop path; physical e-stop button required (not in software)
- **F-015** (perception): Person not detected — None in software: depends on the (external) model; thresholds untuned
- **F-028** (monitoring): Alert rules wrong or never loaded — Rules generated from code; NOT validated with promtool/amtool
- **F-030** (command-center): Queued e-stop lost on restart — None: queue is in memory
- **F-035** (installer): ROS repository key not pinned — None: key fetched over HTTPS without fingerprint pinning
- **F-036** (interfaces): State enum drifts between Python/ROS/protobuf/OpenAPI — Documented rule only; no automatic check

## Założenia i ograniczenia

- **Oceny S/O/D są szacunkami autora, nie danymi z eksploatacji.** Wymagają przeglądu przez
  właściciela bezpieczeństwa, który powinien też ustalić próg RPN (100 to placeholder).
- Wpis „Verified by” oznacza, że istnieje test sprawdzający środek zaradczy w izolacji; nie
  dowodzi, że działa na robocie.
- Środki bez wpisu w „Verified by” nie są wdrożone lub nie mają testu — patrz „Luki”.
- To nie jest formalna analiza zgodna z normą (np. IEC 60812); dokument nie został zatwierdzony.

## Historia zmian

| Wersja | Data | Zmiana |
|---|---|---|
| 2.0 | 2026-10-27 | Pełna lista 36 rodzajów błędów, powiązanie z testami, lista luk |
| 1.0 | 2026-10-27 | Wersja robocza (4 wpisy, `initial_modes`) |
