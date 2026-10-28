# guardian-docs

Generatory dokumentów (Markdown) i kontrole spójności. Czysty Python; `make test` (16 testów).

| Moduł | Zadanie |
|---|---|
| `fmea` | `FailureMode` z S/O/D (1–10) → RPN; `needs_action` przy RPN ≥ 100 lub S ≥ 9; `validate` wymaga mitygacji; tabela sortowana po RPN |
| `rtm` | macierz śledzenia wymagań → testy; `validate` (brak testu, nieistniejący test, duplikaty), `coverage` |
| `sat` | procedura odbioru (kroki + miejsce na wynik); `signoff` tylko gdy każdy krok to dokładnie `PASS` |
| `sac` | kryteria akceptacji z progami; brak pomiaru lub NaN = niezaliczone |
| `architecture` | mapa zależności komponentów, wykrywanie cykli i niezdefiniowanych komponentów, diagram Mermaid |
| `nza`, `ukdp` | rejestry dokumentów (`draft → review → approved → obsolete`; zatwierdza ktoś inny niż właściciel) |

## Założenia i braki

- **Nie znam znaczenia skrótów NZA i UKDP** — oba to na razie ten sam ogólny rejestr dokumentów
  (`register.py`). Podaj, czym są, a dopasuję pola.
- SAT/SAC jak w `guardian-testing` (Site Acceptance Test/Criteria); progi to placeholdery.
- Oceny S/O/D w `fmea.initial_modes()` i próg RPN 100 to **moje szacunki** — wymagają przeglądu
  przez właściciela bezpieczeństwa. Nie jest to formalna analiza FMEA.
- `architecture.DEPENDENCIES` to moja propozycja kierunków zależności, nie wynik analizy kodu.
- Brak eksportu do PDF/DOCX i brak automatycznego łączenia RTM z faktycznymi testami.

## Dokumenty kontrolowane (`docs/`)

| Dokument | Plik | Uwagi |
|---|---|---|
| FMEA v2.0 | `docs/fmea/FMEA-v2.0.md` | **generowany**: `PYTHONPATH=src python3 -m guardian_docs.build .` z `fmea/v2.py`; test pilnuje zgodności |
| NZA v1.0 | `docs/nza/NZA-v1.0.md` | architektura bezpieczeństwa; zawiera listę luk i mapowanie nazw pakietów |
| UKDP v1.0 | `docs/ukdp/UKDP-v1.0.md` | standard dokumentacji; `ukdp.check(text)` sprawdza nagłówek i sekcje |

Wszystkie mają status `szkic` i właściciela „do ustalenia”; oceny w FMEA to szacunki.
