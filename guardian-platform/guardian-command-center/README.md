# guardian-command-center

Logika konsoli operatora dla floty. Czysty Python, zegar wstrzykiwany; `make test` (12 testów).
Nie ma serwera ani interfejsu — to warstwa logiki, którą podłącza się pod `guardian-web`/API.

| Moduł | Zadanie |
|---|---|
| `fleet_manager` | rejestr floty (online/stale/unknown), kolejka poleceń z kontrolą roli; **e-stop dozwolony dla każdej znanej roli**, idzie na początek kolejki i działa też dla nieaktywnych robotów; `estop_all`; pozostałe polecenia tylko dla robota online i roli ≥ operator |
| `incident_manager` | `open → acknowledged → resolved`; deduplikacja (robot, rodzaj); `overdue` wg terminów potwierdzenia |
| `tactical_map` | pozycje robotów i status geofence w strukturze GeoJSON-podobnej; brak pozycji/nieaktywny/poza strefą = alert |
| `mission_overview` | stany misji, jedna aktywna misja na robota, wykrywanie „zawieszonych” |
| `analytics` | MTTA, liczby wg ważności, skuteczność misji, dostępność; brak danych = `None`, nie 0 |

## Założenia i braki

- Role (`viewer < operator < admin`), lista poleceń i terminy potwierdzenia (60 s … 3600 s wg
  ważności 1–4) to moje założenia. Uwierzytelnianie nie istnieje — `operator` i `role` są
  przyjmowane z wejścia, więc podmieniać je musi warstwa API po weryfikacji tożsamości.
- Współrzędne są płaskie (metry), więc wynik nie jest poprawnym GeoJSON dla narzędzi GIS.
- Kolejka poleceń jest w pamięci: po restarcie przepada (w tym niedostarczony e-stop).
- Brak dostarczania poleceń do robota (MQTT/ROS) i brak trwałego dziennika audytu.
- Kolejna kopia testu punkt-w-wielokącie.
