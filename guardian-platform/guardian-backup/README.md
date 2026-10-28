# guardian-backup

Trwałość stanu robota po awarii zasilania lub procesu. Czysty Python, bez zależności.
Nic nie jest jeszcze podłączone do `guardian-core` (jego `snapshot_manager` działa osobno).

| Moduł | Zadanie |
|---|---|
| `hash` | SHA-256 (bajty, pliki, kanoniczny JSON), porównanie w stałym czasie |
| `snapshot` | **atomowy zapis** (plik tymczasowy → `fsync` → `rename` → `fsync` katalogu), numerowane generacje, weryfikacja SHA-256 przy odczycie |
| `journaling` | dziennik tylko-dopisywany z łańcuchem haszy; uszkodzony lub urwany ogon jest wykrywany i obcinany |
| `recovery` | ostatni poprawny snapshot + odtworzenie dziennika; `plan_auto_resume` (**Auto Resume**) |
| `rollback` | cofnięcie do wskazanej generacji; nowsze snapshoty są odkładane do `rolled_back/`, nie kasowane |
| `retention` | zachowuje ostatnie N i świeże; nigdy nie usuwa najnowszego poprawnego snapshotu ani obcych plików |

## Zasady bezpieczeństwa

- Uszkodzony snapshot (zły hash, śmieci, brak pliku) nigdy nie jest używany; odczyt przechodzi do starszego.
- Rollback do uszkodzonej generacji nie przenosi niczego.
- **Auto Resume tylko proponuje** (`ResumePlan`). Wznowienie musi nadal przejść przez maszynę stanów i
  warstwę bezpieczeństwa. Propozycja `resume` wymaga: włączonej opcji, nieuszkodzonego dziennika,
  świeżego stanu (domyślnie ≤ 300 s) i checkpointu misji; w przeciwnym razie `manual`.
- Brak poprawnego snapshotu → `recover_state` zwraca `None` (start z bezpiecznych ustawień domyślnych).

## Ograniczenia

- SHA-256 wykrywa uszkodzenia i przypadkowe zmiany, **nie** celowe fałszerstwo (brak klucza/podpisu).
- Gwarancje `fsync` zależą od systemu plików i dysku; nie testowano utraty zasilania.
- Dziennik nie jest rotowany; `Journal.entries()` czyta cały plik.
- Progi retencji i 300 s to niedostrojone wartości.

```
make test
```
