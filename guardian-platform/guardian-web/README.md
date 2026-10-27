# guardian-web

Warstwa danych i logiki panelu webowego (model widoku, **bez serwera HTTP i bez frontendu**).
Czysty Python, bez zależności. Uwierzytelnianie, sesje i API nie istnieją — role w `settings`
są sprawdzane tylko jako reguła domenowa i serwer musi je egzekwować dla zalogowanego użytkownika.

| Moduł | Zadanie |
|---|---|
| `fleet` | rejestr robotów z heartbeatem: `online` / `stale` / `offline` / `emergency`, kolejność od najpilniejszych |
| `dashboard` | `build_dashboard` → słownik dla szablonu: ogólny status, liczniki, roboty, alerty |
| `reports` | raport misji jako dane, Markdown, HTML (z escapowaniem) i CSV (ochrona przed formułami) |
| `maps` | wersjonowane definicje map (granice, geofence, waypointy) z walidacją |
| `settings` | walidowane ustawienia; zmiana wymaga roli (`viewer` < `operator` < `admin`) |

## Zasady

- Pusty lub nieznany stan floty to `unknown`, nigdy `ok`. Nieznana ważność alertu = krytyczna.
- `EMERGENCY_STOP` jest widoczny, dopóki robot nie zgłosi innego stanu lub nie przejdzie w `offline`.
- Niepoprawne heartbeaty (zły id, bateria spoza 0–100, NaN) są odrzucane.
- Raport: niepoprawne zdarzenia są liczone, nie gubione po cichu; HTML jest escapowany, a komórki CSV
  zaczynające się od `= + - @` dostają prefiks `'`.
- Mapa musi mieć geofence z niezerowym polem, mieszczący się w granicach; waypointy w granicach.
  To tylko wczesna walidacja — decyduje `guardian-safety-layer` na robocie.
- Osłabienie bezpieczeństwa (`require_command_confirmation`, `session_timeout_min`) wymaga roli `admin`.

## Braki

- Serwer, uwierzytelnianie, CSRF, TLS, frontend, trwałe przechowywanie (mapy i ustawienia są w pamięci).
- Progi (10 s / 60 s) i podział ról są moimi założeniami.

```
make test
```
