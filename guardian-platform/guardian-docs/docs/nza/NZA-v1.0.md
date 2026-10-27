# NZA v1.0 — architektura bezpieczeństwa

**ID:** NZA-001
**Wersja:** 1.0
**Status:** szkic
**Właściciel:** do ustalenia
**Data:** 2026-10-27

> „NZA” rozumiem jako *architekturę bezpieczeństwa* (zgodnie z Twoim opisem). Rozwinięcie skrótu
> nie zostało podane.

## Cel

Opisać, jak system Guardian ma zapewniać bezpieczeństwo robota, które środki **istnieją w kodzie
i mają testy**, a które są tylko zamierzone. Dokument jest powiązany z `FMEA-v2.0.md`.

## Zakres

Komponenty `guardian-platform`. Poza zakresem: sprzęt Go2, fizyczny wyłącznik awaryjny, sieć,
certyfikacja. Nie jest to dowód bezpieczeństwa.

## Zasady architektury

1. **Fail-closed.** Dane brakujące, stare, nieskończone lub niezrozumiałe oznaczają „niebezpiecznie”
   albo „nieznane”, nigdy „w porządku” (np. lidar bez odczytów → `None`, a nie „wolne”).
2. **E-stop ma pierwszeństwo.** `emergency_stop` jest dozwolony z każdego źródła i stanu, jest
   zatrzaskiwany, a wyjść z niego można tylko jawnym działaniem operatora.
3. **Stan może się tylko zaostrzać.** `SafetyFSM` eskaluje; obniżenie poziomu wymaga resetu,
   a reset z `EMERGENCY_STOP` jest zabroniony.
4. **Niezaufane źródła nic nie uruchamiają.** Źródła `none` i `web` mogą tylko zatrzymać robota.
5. **LLM nie decyduje sam.** Intencje wykonawcze od LLM wymagają pewności ≥ 0,8 i przechodzą przez
   politykę stanu; `recover` pochodzi wyłącznie z reguł.
6. **Odzyskiwanie nie udaje sukcesu.** Snapshot musi przejść schemat i SHA-256; brak ważnego
   snapshotu, uszkodzony dziennik lub zły wynik zdrowia dają `FAILED`.
7. **Zapisy są atomowe.** Snapshot: plik tymczasowy → fsync → rename → fsync katalogu.
8. **Wstrzykiwany czas.** Zegar jest parametrem, więc zachowanie przy starych danych da się testować.

## Warstwy i odpowiedzialności

| Warstwa | Komponenty | Rola |
|---|---|---|
| Wejście poleceń | `guardian-voice`, `guardian-mobile`, `guardian-web`, `guardian-command-center` | przyjmują polecenia; nie decydują |
| Decyzja | `guardian-ai-engine` | intencja → plan → polityka (źródło, stan, pewność) |
| Bezpieczeństwo | `guardian-safety-layer` | e-stop, FSM, watchdog, geofence, bateria, ryzyko, failover |
| Wykonanie | `guardian-core`, `guardian-mission-manager`, `guardian-navigation`, `guardian-go2-driver` | stan, misje, trasa, sterowanie |
| Percepcja | `guardian-perception` | przeszkody, osoby, zdarzenia (dane „nieznane” ≠ „wolne”) |
| Trwałość | `guardian-backup`, `guardian-core/recovery_engine` | snapshot, dziennik, odzyskiwanie |
| Obserwowalność | `guardian-telemetry`, `guardian-monitoring` | metryki, alerty; stare dane = `guardian_up 0` |
| Łańcuch dostaw | `guardian-devops`, `guardian-installer` | lint CI, skan sekretów, manifest SHA-256, instalacja na sucho |

## Mapowanie nazw pakietów

Lista nazw, którą podałeś (`guardian_interfaces`, `guardian_core`, `guardian_watchdog`,
`guardian_safety`, `guardian_integrity`, `guardian_backup`, `guardian_recovery`, `guardian_audit`,
`guardian_exporter`), nie pokrywa się 1:1 z obecnymi pakietami. Stan faktyczny:

| Nazwa docelowa | Obecna realizacja | Stan |
|---|---|---|
| `guardian_interfaces` | `guardian-interfaces` (msg/srv/action, proto, OpenAPI) | jest, bez importów w kodzie |
| `guardian_core` | `guardian-core` | jest |
| `guardian_watchdog` | `guardian_safety_layer.watchdog`, `guardian_core.watchdog` | rozproszony, dwie kopie |
| `guardian_safety` | `guardian-safety-layer` | jest |
| `guardian_integrity` | `guardian_core.integrity_checker`, `guardian_backup.hash` | rozproszony |
| `guardian_backup` | `guardian-backup` | jest |
| `guardian_recovery` | `guardian_core.recovery_engine`, `guardian_backup.recovery` | dwie niepołączone implementacje |
| `guardian_audit` | `guardian_core.audit` | **tylko szkielet, niezaimplementowany** |
| `guardian_exporter` | `guardian_monitoring.exporters` | jest |

Zmiana nazw lub scalenie wymaga Twojej decyzji; nie wprowadziłem jej.

## Znane luki (z FMEA v2.0)

- **Brak uwierzytelniania i audytu** (`guardian_core.auth`, `guardian_core.audit` to szkielety):
  rola i operator w `command-center` są przyjmowane z wejścia bez weryfikacji.
- **Kolejka poleceń w pamięci** — niedostarczony e-stop przepada po restarcie (F-030).
- **Brak sprzętowego wyłącznika w modelu** — „stop” głosowy może zawieść w hałasie (F-009).
- **Brak weryfikacji narzędziami zewnętrznymi**: promtool/amtool, `colcon`, Gazebo/RViz (F-028).
- **Klucz repozytorium ROS niepinowany** (F-035); **enum stanu w czterech miejscach bez
  automatycznej kontroli** (F-036).
- Komponenty nie są jeszcze ze sobą połączone; testy integracyjne używają atrapy robota.

## Założenia i ograniczenia

- Progi (pewność 0,8 / 0,6, bateria 30 %, opóźnienie e-stop 0,5 s, wiek telemetrii 5 s) to placeholdery.
- Zasady opisują zamierzone zachowanie potwierdzone testami jednostkowymi, nie zachowanie na robocie.
- Dokument nie zastępuje analizy zagrożeń (HARA) ani certyfikacji.

## Historia zmian

| Wersja | Data | Zmiana |
|---|---|---|
| 1.0 | 2026-10-27 | Pierwsza wersja: zasady, warstwy, mapowanie nazw, luki |
