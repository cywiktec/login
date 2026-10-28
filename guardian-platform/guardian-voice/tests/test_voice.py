import math
import unittest

from guardian_voice.command_pipeline import (
    HANDLED, HANDLER_ERROR, IGNORED, LOW_CONFIDENCE, STT_FAILED, CommandPipeline,
)
from guardian_voice.noise_reduction import HighPass, NoiseGate, NoiseReducer, rms
from guardian_voice.speech_to_text import FakeSTT, STTError, Transcript, safe_transcribe
from guardian_voice.text_to_speech import FakeTTS, Speaker
from guardian_voice.wakeword import WakeSession, WakeWordDetector

LOUD = [[0.5 * math.sin(i) for i in range(160)]]
QUIET = [[0.001] * 160]


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class NoiseTests(unittest.TestCase):
    def test_gate(self):
        gate = NoiseGate(threshold=0.02)
        out, speech = gate.process([0.001] * 10)
        self.assertEqual((out, speech), ([0.0] * 10, False))
        out, speech = gate.process([0.3, -0.3] * 5)
        self.assertTrue(speech)
        self.assertEqual(out, [0.3, -0.3] * 5)

    def test_adaptive_gate_raises_threshold(self):
        gate = NoiseGate(threshold=0.01, adaptive=True, margin=3.0)
        for _ in range(20):
            gate.process([0.05] * 10)  # steady noise, first frame is judged speech
        gate.process([0.005] * 10)
        self.assertEqual(rms(gate.process([0.005] * 10)[0]), 0.0)

    def test_highpass_removes_dc(self):
        hp = HighPass(0.95)
        out = hp.process([0.5] * 400)
        self.assertLess(abs(out[-1]), 0.001)

    def test_validation(self):
        with self.assertRaises(ValueError):
            HighPass(1.0)
        with self.assertRaises(ValueError):
            NoiseGate(-1)

    def test_reducer(self):
        reducer = NoiseReducer()
        self.assertTrue(reducer.process(LOUD[0])[1])
        self.assertFalse(reducer.process(QUIET[0])[1])


class STTTests(unittest.TestCase):
    def test_safe_transcribe(self):
        self.assertEqual(safe_transcribe(FakeSTT(["a"]), []).text, "a")
        self.assertIsNone(safe_transcribe(FakeSTT([STTError("x")]), []))
        self.assertIsNone(safe_transcribe(FakeSTT([]), []))
        self.assertIsNone(safe_transcribe(FakeSTT([Transcript(None)]), []))


class TTSTests(unittest.TestCase):
    def test_sanitizes_and_limits(self):
        tts = FakeTTS()
        speaker = Speaker(tts, max_chars=10)
        self.assertTrue(speaker.say("a\x00b\n\n  c" + "x" * 50))
        self.assertEqual(tts.spoken, ["a b cxxxxx"])
        self.assertFalse(speaker.say("  \n "))

    def test_engine_failure_is_swallowed(self):
        self.assertFalse(Speaker(FakeTTS(fail=True)).say("hi"))


class WakeWordTests(unittest.TestCase):
    def test_detect(self):
        d = WakeWordDetector()
        self.assertEqual(d.detect("MISIEK, wróć do bazy."), "wróć do bazy.")
        self.assertEqual(d.detect("Misiek raport stanu"), "raport stanu")
        self.assertEqual(d.detect("Misiec, raport"), "raport")  # close misrecognition
        self.assertIsNone(d.detect("Misiu, raport"))  # too far
        self.assertEqual(d.detect("misiek"), "")
        self.assertIsNone(d.detect("powiedz misiek wróć"))
        self.assertIsNone(d.detect("kot wraca do bazy"))
        self.assertIsNone(d.detect(""))

    def test_bare_wake_word_arms_window(self):
        clock = Clock()
        session = WakeSession(window=5, clock=clock)
        self.assertIsNone(session.feed("misiek"))
        self.assertTrue(session.armed)
        clock.t = 3
        self.assertEqual(session.feed("rozpocznij patrol"), "rozpocznij patrol")
        self.assertIsNone(session.feed("rozpocznij patrol"))  # window consumed

    def test_window_expires(self):
        clock = Clock()
        session = WakeSession(window=5, clock=clock)
        session.feed("misiek")
        clock.t = 6
        self.assertIsNone(session.feed("rozpocznij patrol"))


class PipelineTests(unittest.TestCase):
    def build(self, results, handler=None, **kwargs):
        self.commands = []

        def default(command):
            self.commands.append(command)
            return "ok"

        self.tts = FakeTTS()
        return CommandPipeline(FakeSTT(results), handler or default, Speaker(self.tts), **kwargs)

    def test_happy_path(self):
        p = self.build(["MISIEK, wróć do bazy."])
        result = p.process(LOUD)
        self.assertEqual(result.status, HANDLED)
        self.assertEqual(self.commands, ["MISIEK, wróć do bazy."])
        self.assertEqual(self.tts.spoken, ["ok"])

    def test_silence_skips_stt(self):
        p = self.build([])
        self.assertEqual(p.process(QUIET).status, IGNORED)
        self.assertEqual(p.stt.calls, 0)

    def test_no_wake_word_is_ignored(self):
        p = self.build(["rozpocznij patrol"])
        self.assertEqual(p.process(LOUD).status, IGNORED)
        self.assertEqual(self.commands, [])

    def test_two_step_wake(self):
        p = self.build(["misiek", "rozpocznij patrol"])
        self.assertEqual(p.process(LOUD).status, IGNORED)
        self.assertEqual(p.process(LOUD).command, "MISIEK, rozpocznij patrol")

    def test_low_confidence_rejected(self):
        p = self.build([Transcript("MISIEK, rozpocznij patrol", 0.3)])
        self.assertEqual(p.process(LOUD).status, LOW_CONFIDENCE)
        self.assertEqual(self.commands, [])

    def test_nan_confidence_rejected(self):
        p = self.build([Transcript("MISIEK, rozpocznij patrol", float("nan"))])
        self.assertEqual(p.process(LOUD).status, LOW_CONFIDENCE)

    def test_stt_failure(self):
        self.assertEqual(self.build([STTError("x")]).process(LOUD).status, STT_FAILED)

    def test_bare_stop_works_without_wake_word(self):
        p = self.build(["Stop!"])
        self.assertEqual(p.process(LOUD).command, "MISIEK, stop")

    def test_bare_stop_can_be_disabled(self):
        p = self.build(["stop"], allow_bare_stop=False)
        self.assertEqual(p.process(LOUD).status, IGNORED)

    def test_bare_stop_still_needs_confidence(self):
        p = self.build([Transcript("stop", 0.1)])
        self.assertEqual(p.process(LOUD).status, LOW_CONFIDENCE)

    def test_handler_error_is_contained(self):
        def boom(command):
            raise RuntimeError("bad")

        p = self.build(["MISIEK, raport stanu"], handler=boom)
        result = p.process(LOUD)
        self.assertEqual(result.status, HANDLER_ERROR)
        self.assertEqual(self.tts.spoken, ["Błąd wykonania komendy."])


if __name__ == "__main__":
    unittest.main()
