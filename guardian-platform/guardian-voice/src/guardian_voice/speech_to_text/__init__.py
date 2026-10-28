"""Speech-to-text interface. No real engine is bundled."""

from dataclasses import dataclass


class STTError(RuntimeError):
    pass


@dataclass(frozen=True)
class Transcript:
    text: str
    confidence: float = 1.0  # 0..1; engines without a score should report a conservative value


class SpeechToText:
    def transcribe(self, audio):
        raise NotImplementedError


class FakeSTT(SpeechToText):
    """Scripted results in order; an Exception entry is raised, None means nothing heard."""

    def __init__(self, results):
        self._results = list(results)
        self.calls = 0

    def transcribe(self, audio):
        self.calls += 1
        if not self._results:
            raise STTError("no scripted result left")
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        if isinstance(result, str):
            return Transcript(result)
        return result


def safe_transcribe(engine, audio):
    """Never raises: engine failures become None."""
    try:
        result = engine.transcribe(audio)
    except Exception:
        return None
    if not isinstance(result, Transcript) or not isinstance(result.text, str):
        return None
    return result
