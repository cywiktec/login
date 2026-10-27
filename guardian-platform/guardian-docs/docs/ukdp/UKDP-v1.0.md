# UKDP v1.0 — standard dokumentacji

**ID:** UKDP-001
**Wersja:** 1.0
**Status:** szkic
**Właściciel:** do ustalenia
**Data:** 2026-10-27

> „UKDP” rozumiem jako *standard dokumentacji* (zgodnie z Twoim opisem). Rozwinięcie skrótu
> nie zostało podane.

## Cel

Ujednolicić dokumenty kontrolowane projektu, aby dało się je sprawdzać automatycznie
(`guardian_docs.ukdp.check`) i śledzić ich status.

## Zakres

Dokumenty w `guardian-docs/docs/` (NZA, FMEA, RTM, SAT, SAC, architektura, UKDP). README
komponentów są poza zakresem.

## Reguły

**Nagłówek** — bezpośrednio po tytule `# …`, każde pole w osobnej linii w formacie `**Pole:** wartość`:

| Pole | Format |
|---|---|
| ID | `FMEA`, `NZA`, `UKDP`, `RTM`, `SAT`, `SAC` lub `ARCH` + `-` + trzy cyfry, np. `NZA-001` |
| Wersja | `MAJOR.MINOR`, np. `1.0` |
| Status | `szkic` → `przegląd` → `zatwierdzony` → `wycofany` |
| Właściciel | osoba lub rola; `do ustalenia`, gdy nie wyznaczono |
| Data | `RRRR-MM-DD` |

**Wymagane sekcje** (`##`): `Cel`, `Zakres`, `Założenia i ograniczenia`, `Historia zmian`.

**Zasady treści**

1. Język polski; identyfikatory i kod bez tłumaczenia.
2. Każde twierdzenie o zachowaniu systemu wskazuje dowód (test, plik) albo jest oznaczone jako
   założenie. Brak dowodu to luka i trafia na listę luk, nie jest pomijany.
3. Liczby bez źródła (progi, oceny) są oznaczone jako placeholder lub szacunek.
4. Dokumenty generowane noszą uwagę „nie edytuj ręcznie” i wskazują generator.

**Cykl życia i zatwierdzanie**

- Status zmienia się tylko po kolei: szkic → przegląd → zatwierdzony → wycofany;
  z przeglądu można wrócić do szkicu.
- Zatwierdzić może osoba **inna niż właściciel** (`Register.transition`).
- Zmiana treści zatwierdzonego dokumentu podnosi wersję i dopisuje wiersz do „Historia zmian”;
  poprzednie wiersze się nie zmieniają.

## Założenia i ograniczenia

- Zatwierdzanie jest tylko regułą w kodzie rejestru; nie ma uwierzytelniania ani podpisów,
  więc nie jest to kontrola prawdziwej tożsamości.
- Wartość `Właściciel` nie jest sprawdzana względem żadnej listy osób.
- Standard nie wymusza treści merytorycznej, tylko strukturę.

## Historia zmian

| Wersja | Data | Zmiana |
|---|---|---|
| 1.0 | 2026-10-27 | Pierwsza wersja: nagłówek, sekcje, zasady treści, cykl życia |
