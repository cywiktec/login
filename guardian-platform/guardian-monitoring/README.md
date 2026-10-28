# guardian-monitoring

Generatory konfiguracji i eksporter metryk dla monitoringu platformy. Czysty Python, bez
zależności (PyYAML opcjonalnie, tylko w testach). **Wygenerowane pliki nie były sprawdzone
przez `promtool`, `amtool` ani Grafanę** — testy sprawdzają je wyłącznie jako poprawny
YAML/JSON i spójność nazw metryk. Nie ma uruchomionego Prometheusa/Grafany/Alertmanagera.

| Moduł | Zadanie |
|---|---|
| `prometheus` | format tekstowy metryk (z escapowaniem etykiet), `prometheus.yml` |
| `exporters` | `GuardianExporter`: dane robota → metryki `guardian_*` |
| `alertmanager` | reguły alertów (`Rule`, `DEFAULT_RULES`) i `alertmanager.yml` |
| `dashboards` | specyfikacje paneli niezależne od Grafany |
| `grafana` | JSON dashboardu i pliki provisioningu (źródło danych, dashboardy) |
| `yamlout` | mały emiter YAML; napisy zawsze jako cytowane, więc wartość nie wyjdzie poza swoją linię |

## Zasady

- Brak świeżych danych → `guardian_up 0`, odczyty pomijane. Nieświeże, przyszłe, spoza zakresu
  lub nie-liczbowe wartości nigdy nie są eksportowane jako zdrowe.
- Alert `GuardianDown` (brak danych) jest krytyczny, a testy pilnują, że każda metryka użyta w
  regułach i panelach faktycznie jest eksportowana.
- Webhook Alertmanagera musi być `https://`; odbiorca to placeholder do zastąpienia prawdziwym.
- Progi alertów (baterii 10/20 %, dysk 90 %, czasy `for`) są niedostrojone.

## Braki

- Brak serwera HTTP `/metrics` — `render_metrics(exporter.collect())` zwraca tekst do podania.
- Brak logów (Loki itp.), brak uwierzytelniania, wersja schematu Grafany (39) to założenie.

```
make test            # z PyYAML (np. venv) uruchamia też testy parsowania YAML
```
