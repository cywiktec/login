# guardian-voice

Interfejs głosowy MISIEK AI Guardian. Czysty Python, bez zależności. **Brak prawdziwego
silnika STT/TTS/wakeword audio**: są interfejsy i atrapy (`FakeSTT`, `FakeTTS`); nic
nie było uruchamiane z mikrofonem ani na robocie.

Przepływ: ramki audio → `noise_reduction` → `speech_to_text` → `wakeword` → tekst
`MISIEK, <fraza>` → handler (np. parser z guardian-ai-engine) → `text_to_speech`.

| Moduł | Zadanie |
|---|---|
| `noise_reduction` | filtr górnoprzepustowy + bramka szumów (opcjonalnie adaptacyjna) |
| `speech_to_text` | interfejs `SpeechToText`, `FakeSTT`, `safe_transcribe` (błędy → `None`) |
| `text_to_speech` | interfejs `TextToSpeech`, `Speaker` (czyści tekst, limit 300 znaków, połyka błędy) |
| `wakeword` | wykrywa „MISIEK" na początku transkrypcji (rozmyte, bez polskich znaków); samo „MISIEK" otwiera okno 5 s |
| `command_pipeline` | łączy całość, zwraca `PipelineResult` ze statusem |

## Zasady bezpieczeństwa

- Cisza (bramka) nie trafia do STT; wynik STT o pewności poniżej 0,6 (lub NaN) jest odrzucany.
- Komenda bez słowa wybudzenia jest ignorowana.
- Wyjątek: samo „stop" działa bez „MISIEK" (`allow_bare_stop`, domyślnie włączone) — zatrzymanie nie może zależeć od rozpoznania imienia. Wymaga to wciąż odpowiedniej pewności STT i zadziała tylko, jeśli handler/polityka pozwolą.
- Błędy STT, TTS i handlera są izolowane; handler zawsze dostaje tylko tekst, nigdy surowe audio.

## Założenia i braki

- Wakeword działa na transkrypcie, nie na dźwięku, więc STT musi nasłuchiwać stale; osobny model audio to TODO.
- Próg szumów 0,02, pewność 0,6 i okno 5 s są niedostrojonymi wartościami.
- Brak segmentacji wypowiedzi (VAD) i odtwarzania audio; `process()` dostaje jedną wypowiedź.
- Nic nie jest podłączone do guardian-core.

```
make test
```
