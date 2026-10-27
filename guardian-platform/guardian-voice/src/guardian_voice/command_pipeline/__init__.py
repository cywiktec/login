"""audio -> noise reduction -> STT -> wake word -> command text -> handler -> spoken reply."""

from dataclasses import dataclass
from typing import Optional

from ..noise_reduction import NoiseReducer
from ..speech_to_text import safe_transcribe
from ..text_to_speech import Speaker
from ..wakeword import WakeSession

# Spoken without the wake word, because stopping must never depend on recognizing "MISIEK".
SAFETY_WORDS = {"stop", "awaryjny stop"}

IGNORED = "ignored"  # no speech, or no wake word
LOW_CONFIDENCE = "low_confidence"
STT_FAILED = "stt_failed"
HANDLED = "handled"
HANDLER_ERROR = "handler_error"


@dataclass(frozen=True)
class PipelineResult:
    status: str
    command: Optional[str] = None
    reply: Optional[str] = None
    transcript: str = ""


def _plain(text):
    return " ".join(text.lower().strip(" .!?,").split())


class CommandPipeline:
    def __init__(self, stt, handler, speaker=None, reducer=None, session=None,
                 min_confidence=0.6, min_speech_frames=1, allow_bare_stop=True):
        """handler(command_text) -> reply string or None. Command text is formatted
        "MISIEK, <phrase>" to match what guardian-core and guardian-ai-engine parse."""
        self.stt = stt
        self.handler = handler
        self.speaker = speaker
        self.reducer = reducer or NoiseReducer()
        self.session = session or WakeSession()
        self.min_confidence = min_confidence
        self.min_speech_frames = min_speech_frames
        self.allow_bare_stop = allow_bare_stop

    def process(self, frames):
        """Handle one utterance: an iterable of audio frames."""
        cleaned, speech = [], 0
        for frame in frames:
            out, is_speech = self.reducer.process(frame)
            cleaned.extend(out)
            speech += is_speech
        if speech < self.min_speech_frames:
            return PipelineResult(IGNORED)

        transcript = safe_transcribe(self.stt, cleaned)
        if transcript is None:
            return PipelineResult(STT_FAILED)
        text = transcript.text
        if not text.strip():
            return PipelineResult(IGNORED)
        confidence = transcript.confidence
        if not isinstance(confidence, (int, float)) or not confidence >= self.min_confidence:
            return PipelineResult(LOW_CONFIDENCE, transcript=text)

        if self.allow_bare_stop and _plain(text) in SAFETY_WORDS:
            return self._dispatch("MISIEK, stop", text)

        command = self.session.feed(text)
        if not command:
            return PipelineResult(IGNORED, transcript=text)
        return self._dispatch(f"MISIEK, {command}", text)

    def _dispatch(self, command, transcript):
        try:
            reply = self.handler(command)
        except Exception as error:
            reply = "Błąd wykonania komendy."
            self._say(reply)
            return PipelineResult(HANDLER_ERROR, command, f"{type(error).__name__}: {error}", transcript)
        if reply:
            self._say(reply)
        return PipelineResult(HANDLED, command, reply, transcript)

    def _say(self, text):
        if self.speaker is not None:
            self.speaker.say(text)
