"""Generates docs/fmea/FMEA-v2.0.md from guardian_docs.fmea.v2. Run: python -m guardian_docs.build"""

import os
import sys
from collections import Counter

from . import fmea
from .fmea import v2

HEADER = """# FMEA v2.0 — analiza rodzajów i skutków błędów

**ID:** FMEA-001
**Wersja:** 2.0
**Status:** szkic
**Właściciel:** do ustalenia
**Data:** 2026-10-27

> Dokument generowany z `guardian_docs/fmea/v2.py` (`python -m guardian_docs.build`).
> Nie edytuj ręcznie — zmień dane i wygeneruj ponownie.

## Cel

Wskazać rodzaje błędów komponentów Guardian, ich skutki, zastosowane środki zaradcze i dowody ich
weryfikacji, tak aby było widać luki, a nie tylko pokrycie.

## Zakres

Komponenty monorepo `guardian-platform` (stan kodu z daty dokumentu). Nie obejmuje sprzętu
Unitree Go2, sieci, ani procesu produkcyjnego.

## Metoda

RPN = S × O × D (każde 1–10; D=10 oznacza praktycznie niewykrywalny).
Wymaga działania: RPN ≥ {limit} **lub** S ≥ 9. Kolumna „Verified by” wskazuje test w repozytorium;
`-` oznacza brak dowodu (luka).

"""

FOOTER = """
## Założenia i ograniczenia

- **Oceny S/O/D są szacunkami autora, nie danymi z eksploatacji.** Wymagają przeglądu przez
  właściciela bezpieczeństwa, który powinien też ustalić próg RPN ({limit} to placeholder).
- Wpis „Verified by” oznacza, że istnieje test sprawdzający środek zaradczy w izolacji; nie
  dowodzi, że działa na robocie.
- Środki bez wpisu w „Verified by” nie są wdrożone lub nie mają testu — patrz „Luki”.
- To nie jest formalna analiza zgodna z normą (np. IEC 60812); dokument nie został zatwierdzony.

## Historia zmian

| Wersja | Data | Zmiana |
|---|---|---|
| 2.0 | 2026-10-27 | Pełna lista {n} rodzajów błędów, powiązanie z testami, lista luk |
| 1.0 | 2026-10-27 | Wersja robocza (4 wpisy, `initial_modes`) |
"""


def render():
    modes = v2.modes()
    problems = fmea.validate(modes)
    if problems:
        raise ValueError("; ".join(problems))
    actions = [m for m in modes if m.needs_action]
    gaps = fmea.unverified(modes)
    by_comp = Counter(m.component for m in modes)
    out = [HEADER.format(limit=fmea.RPN_LIMIT)]
    out.append("## Podsumowanie\n")
    out.append(f"- Rodzajów błędów: {len(modes)}; wymagających działania: {len(actions)}.\n")
    out.append(f"- Wymagających działania **bez dowodu weryfikacji (luki): {len(gaps)}**.\n")
    out.append("- Wg komponentu: " + ", ".join(f"{c} ({n})" for c, n in sorted(by_comp.items())) + ".\n\n")
    out.append("## Tabela\n\n")
    out.append(fmea.render(modes))
    out.append("\n## Luki\n\n")
    if gaps:
        by_id = {m.id: m for m in modes}
        out.append("Rodzaje błędów wymagające działania, dla których nie ma testu:\n\n")
        out.extend(f"- **{i}** ({by_id[i].component}): {by_id[i].mode} — {by_id[i].mitigation}\n" for i in gaps)
    else:
        out.append("Brak.\n")
    out.append(FOOTER.format(limit=fmea.RPN_LIMIT, n=len(modes)))
    return "".join(out)


def path(root):
    return os.path.join(root, "docs", "fmea", "FMEA-v2.0.md")


def main(root="."):
    target = path(root)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(render())
    os.replace(tmp, target)
    return target


if __name__ == "__main__":
    print(main(sys.argv[1] if len(sys.argv) > 1 else "."))
