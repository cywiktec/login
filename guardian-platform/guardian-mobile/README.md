# guardian-mobile

Logika kliencka aplikacji mobilnej MISIEK (model widoku, **bez UI**). Czysty Python, bez
zależności. Brak natywnej aplikacji (Android/iOS), prawdziwego transportu HTTP i
uwierzytelniania: jest interfejs `Transport` i atrapa `FakeTransport`. Ścieżki `/command`,
`/missions`, `/telemetry` oraz format odpowiedzi `{"ok": true}` to moje założenia —
trzeba je uzgodnić z `guardian-interfaces/openapi/guardian.yaml`.

| Moduł | Zadanie |
|---|---|
| `app` | `GuardianApp`: wysyłanie komend z potwierdzeniem, awaryjny stop, wysyłka misji, odświeżanie telemetrii |
| `maps` | `MapView`: przeliczanie świat ↔ ekran, geofence i trasa jako nakładki |
| `missions` | `MissionDraft` (walidacja waypointów, pętle 1–20, max 50 punktów) i `MissionLibrary` |
| `alerts` | `AlertInbox`: deduplikacja, sortowanie wg ważności, potwierdzanie |
| `telemetry` | `TelemetryView`: walidacja danych i status `no_data` / `stale` / `live` |
| `settings` | walidowane ustawienia zapisywane atomowo; uszkodzony plik → wartości domyślne |

## Zasady bezpieczeństwa

- Komendy wykonawcze (patrol, powrót, przerwanie, wznowienie) wymagają potwierdzenia
  (`confirm_commands`, domyślnie włączone). Stop **nigdy** nie wymaga potwierdzenia ani
  świeżej telemetrii.
- Aplikacja nie zgłasza sukcesu, dopóki robot nie odpowie `ok: true`; błąd sieci to `offline`.
- Nieświeże lub niepoprawne dane telemetrii nie są pokazywane jako aktualne.
- Alert o nieznanej ważności traktowany jest jako krytyczny; powtórzony alert znów wymaga potwierdzenia.
- Kontrole geofence i misji po stronie telefonu to tylko podpowiedź — decyduje robot
  (`guardian-safety-layer`).
- `base_url` musi być `https://`.

## Braki

- UI, push notifications, uwierzytelnianie i przypinanie certyfikatów.
- Pobieranie mapy z robota (`MapView` dostaje tylko granice).

```
make test
```
