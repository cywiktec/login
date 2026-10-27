# guardian-perception

Przetwarzanie danych z sensorów. Czysty Python, bez zależności; `make test` (19 testów).
**Nie uruchamia sieci neuronowej ani nie łączy się z kamerą/lidarem** — przetwarza dane, które
dostarczy sterownik lub model.

| Moduł | Zadanie |
|---|---|
| `camera` | walidacja ramki (wymiary, długość danych, ts), `CameraSource`: odrzuca ramki nieuporządkowane, `latest()` zwraca `None` gdy brak/stara |
| `lidar` | walidacja skanu, odrzucanie NaN/inf/poza zakresem, `min_distance` w sektorze (zbyt wiele złych odczytów = `None`, czyli **nieznane, nie wolne**), klastry przeszkód |
| `yolo` | `Detection`, IoU, NMS per etykieta, `postprocess` (złe wiersze odrzucane i liczone) |
| `object_tracker` | zachłanny tracker IoU, stabilne id, `min_hits`, wygasanie po `max_missed` |
| `person_detection` | filtr osób wg pewności, najbliższa (wysokość ramki), strefa |
| `event_detection` | zdarzenia `person_in_zone`, `motion` (pod intencję „wykryj ruch”), `obstacle_close`; tylko zbocze narastające, ponowne uzbrojenie po ustąpieniu; brak danych nie kasuje aktywnego stanu |

## Założenia i braki

- Progi (pewność 0,6, IoU 0,3/0,5, ruch 5 % wysokości ramki, przeszkoda < 0,8 m, ramka ≤ 0,5 s)
  są nieprzetestowane na prawdziwych danych.
- „Najbliższa osoba” wg wysokości ramki to prymityw bez kalibracji kamery; ruch mierzony w pikselach
  nie odróżnia ruchu osoby od ruchu kamery/robota.
- Tracker nie ma filtru Kalmana ani re-identyfikacji; szybki ruch (brak nakładania ramek) tworzy
  nowy track.
- Lidar tylko 2D; brak fuzji kamera–lidar i układów współrzędnych.
- Zdarzenia nie są jeszcze podłączone do `guardian-ai-engine` (intencja `detect_motion` nie ma
  handlera) ani do `guardian-telemetry`.
