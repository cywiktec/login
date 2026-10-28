# guardian-installer

Instalator platformy na Ubuntu 22.04 i 24.04. Czysty Python, bez zależności.
**Nie był uruchamiany na prawdziwym systemie** (testy używają atrapy wykonawcy): polecenia apt,
klucz ROS i usługa Docker są niesprawdzone, a nazwy pakietów i adresy to moje założenia do weryfikacji.

| Moduł | Zadanie |
|---|---|
| `ubuntu22`, `ubuntu24` | profile: wersja, codename, dystrybucja ROS 2 (`humble` / `jazzy`), Python (3.10 / 3.12) |
| `docker` | kroki instalacji `docker.io` z archiwum Ubuntu (bez zewnętrznego repozytorium) |
| `ros2` | repozytorium apt ROS 2 z kluczem i `ros-<distro>-ros-base` |
| `validation` | kontrola wstępna: system, architektura, dysk ≥ 10 GB, RAM ≥ 2 GB, root |
| `recovery` | stan instalacji (zapis atomowy), wznawianie, wycofanie kroków w odwrotnej kolejności |
| `installer` | `build_plan` i `install` |

## Zasady bezpieczeństwa

- **Domyślnie tryb próbny**: bez `execute=True` nic nie jest wykonywane ani zapisywane.
- Przy `execute=True` nieudana kontrola wstępna (nieznany system, brak roota, mało miejsca,
  nieznany RAM) blokuje wszystko.
- Polecenia to listy argumentów, nigdy ciągi dla powłoki; limit czasu na polecenie.
- Postęp zapisywany po każdym kroku; ponowne uruchomienie pomija wykonane kroki (i te, których
  `check` już przechodzi). Uszkodzony plik stanu = start od nowa.
- Błąd zatrzymuje instalację; `rollback_on_failure=True` cofa wykonane kroki w odwrotnej
  kolejności, a nieudane cofnięcie nie blokuje pozostałych.

## Ograniczenia

- Klucz ROS pobierany po HTTPS, **bez przypięcia odcisku** — warto dodać sumę kontrolną.
- Cofanie `apt-get remove` nie usuwa zależności ani konfiguracji, a nie odtwarza stanu sprzed instalacji.
- Brak instalacji samych komponentów Guardian i konfiguracji usług systemd; brak kroków dla Pythona/venv poza pakietami.
- Brak obsługi proxy, offline i innych wersji Ubuntu.

```
make test
```
