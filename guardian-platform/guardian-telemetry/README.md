# guardian-telemetry

Telemetria robota: wspólny format wiadomości, transporty w pamięci, cache ostatnich wartości
i magazyn zdarzeń. Czysty Python, bez zależności. **Brak prawdziwego brokera MQTT, DDS ani
serwera WebSocket** — wszystko działa w pamięci i nie było testowane z siecią ani robotem.

| Moduł | Zadanie |
|---|---|
| `message` | `TelemetryMessage`: walidacja (`robot_id`, rodzaj, skończony znacznik czasu, limit 16 KiB), JSON |
| `mqtt` | tematy `guardian/<robot_id>/<rodzaj>`, dopasowanie `+`/`#`, `InMemoryBroker` |
| `dds` | tematy z historią KEEP_LAST, normalizacja próbek do wiadomości |
| `websocket` | `Hub`: rozsyłanie do klientów z filtrami i ograniczoną kolejką |
| `snapshots` | cache ostatniej wartości per robot i rodzaj, z wiekiem |
| `event_store` | dziennik JSON Lines (dopisywanie, zapytania); uszkodzone linie pomijane i liczone |

## Zasady

- Wiadomości niepoprawne (zły JSON, NaN, zły temat, temat niezgodny z treścią) są odrzucane i liczone.
- Wolny klient traci najstarsze wiadomości; nigdy nie blokuje nadawcy.
- Błąd jednego odbiorcy nie zatrzymuje pozostałych.
- Starsza wiadomość (wg `ts`) nie nadpisuje nowszej w cache; `get(max_age=...)` nie zwraca nieświeżych danych.
- Pełny magazyn zdarzeń zwraca `False` z `append` zamiast cicho gubić dane — wywołujący musi to obsłużyć.

## Braki

- Brak uwierzytelniania, TLS, QoS i retained messages; wsparcie realnych protokołów to TODO.
- Brak rotacji magazynu (archiwizacja: `guardian-backup`); zapytania czytają cały plik.
- Zestaw rodzajów (`state`, `battery`, `pose`, `health`, `event`, `diagnostics`) i format tematów to moje założenia.

```
make test
```
