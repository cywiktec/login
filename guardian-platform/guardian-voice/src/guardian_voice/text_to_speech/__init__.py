"""Text-to-speech interface and a speaker that sanitizes what it says."""

import re

MAX_CHARS = 300


class TextToSpeech:
    def speak(self, text):
        raise NotImplementedError


class FakeTTS(TextToSpeech):
    def __init__(self, fail=False):
        self.spoken = []
        self.fail = fail

    def speak(self, text):
        if self.fail:
            raise RuntimeError("tts down")
        self.spoken.append(text)


class Speaker:
    """Cleans text (control characters, whitespace, length) and swallows engine errors,
    so a broken speaker can never break command handling."""

    def __init__(self, engine, max_chars=MAX_CHARS):
        self.engine = engine
        self.max_chars = max_chars

    def say(self, text):
        clean = re.sub(r"[\x00-\x1f\x7f]+", " ", str(text))
        clean = re.sub(r"\s+", " ", clean).strip()[: self.max_chars]
        if not clean:
            return False
        try:
            self.engine.speak(clean)
        except Exception:
            return False
        return True
