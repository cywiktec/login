"""Wake word detection on transcripts ("MISIEK"), tolerant of small recognition errors."""

import re
import time
import unicodedata
from difflib import SequenceMatcher


def _norm(text):
    text = unicodedata.normalize("NFKD", text.lower().replace("ł", "l"))
    return "".join(c for c in text if not unicodedata.combining(c))


class WakeWordDetector:
    def __init__(self, word="misiek", min_ratio=0.8):
        self.word = _norm(word)
        self.min_ratio = min_ratio

    def detect(self, text):
        """Return the remaining command text if the utterance *starts* with the wake word,
        else None. The word must be first, so mentions mid-sentence do not trigger."""
        match = re.match(r"\s*([^\s,.:;!?]+)[\s,.:;!?]*(.*)$", text, re.S)
        if not match:
            return None
        first, rest = match.groups()
        if SequenceMatcher(None, _norm(first), self.word).ratio() < self.min_ratio:
            return None
        return rest.strip()


class WakeSession:
    """After a bare wake word ("MISIEK"), the next utterance within `window` seconds
    counts as the command."""

    def __init__(self, detector=None, window=5.0, clock=time.monotonic):
        self.detector = detector or WakeWordDetector()
        self.window = window
        self._clock = clock
        self._armed_until = None

    def feed(self, text):
        """Return command text when one is ready, else None."""
        rest = self.detector.detect(text)
        if rest is not None:
            if rest:
                self._armed_until = None
                return rest
            self._armed_until = self._clock() + self.window
            return None
        if self._armed_until is not None:
            armed, self._armed_until = self._clock() <= self._armed_until, None
            if armed and text.strip():
                return text.strip()
        return None

    @property
    def armed(self):
        return self._armed_until is not None and self._clock() <= self._armed_until
