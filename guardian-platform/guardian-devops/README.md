# guardian-devops

Generatory i kontrole dla CI/CD. Czysty Python, bez zależności; testy: `make test` (20).

| Moduł | Zadanie |
|---|---|
| `github_actions` | generuje workflow (macierz testów per komponent, release po tagu) i `lint` (brak `permissions`, `pull_request_target`, niepiętowane akcje, wstrzykiwanie `github.event` do shella) |
| `docker_compose` | generuje compose (porty tylko na 127.0.0.1, `cap_drop ALL`, `read_only`) i `validate` (tag `latest`, `privileged`, host network, docker.sock, jawne hasła) |
| `releases` | semver (`bump`), wpis w CHANGELOG bez nadpisywania, `check_release` (tag == VERSION) |
| `secrets` | heurystyczny skaner sekretów (wyniki bez wartości), `redact`, `require_env`; nieczytelny plik = wykrycie |
| `artifacts` | `MANIFEST.json` z SHA-256, atomowy zapis, `verify` (brak/zmiana/nadmiarowy plik) |

`yamlout.py` to kopia emitera z `guardian-monitoring` (celowo, by uniknąć zależności).

## Założenia i braki

- Nic nie było uruchomione w prawdziwym GitHub Actions ani `docker compose` — wygenerowany YAML
  nie został zwalidowany przez te narzędzia.
- Akcje są piętowane tagiem głównym (`@v4`), nie SHA commita; SHA jest bezpieczniejsze.
- Wersje obrazów (mosquitto 2, prometheus 2.53.0, grafana 11.1.0, alertmanager 0.27.0) wybrałem
  z pamięci — sprawdź.
- Skaner sekretów jest heurystyką; nie zastępuje np. gitleaks i nie przeszukuje historii gita.
- Moduł `secrets` nie przechowuje sekretów — tylko sprawdza, że zmienne środowiskowe są ustawione.
- Istniejące `.github/workflows` repozytorium nie zostały zmienione.
