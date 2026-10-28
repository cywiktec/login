"""Audio cleanup on plain sample lists (floats in [-1, 1]). No numpy needed."""

import math


def rms(samples):
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


class HighPass:
    """One-pole DC/rumble filter. alpha closer to 1 removes less."""

    def __init__(self, alpha=0.95):
        if not 0 < alpha < 1:
            raise ValueError("alpha must be in (0, 1)")
        self.alpha = alpha
        self._prev_in = 0.0
        self._prev_out = 0.0

    def process(self, samples):
        out = []
        for x in samples:
            y = self.alpha * (self._prev_out + x - self._prev_in)
            self._prev_in, self._prev_out = x, y
            out.append(y)
        return out


class NoiseGate:
    """Zeroes frames whose RMS is below the threshold.

    With adaptive=True the threshold follows a slowly updated noise floor, learned
    only from frames judged to be silence, times `margin`.
    """

    def __init__(self, threshold=0.02, adaptive=False, margin=3.0, smoothing=0.9):
        if threshold < 0:
            raise ValueError("threshold must be >= 0")
        self.threshold = threshold
        self.adaptive = adaptive
        self.margin = margin
        self.smoothing = smoothing
        self._floor = None

    def process(self, frame):
        level = rms(frame)
        threshold = self.threshold
        if self.adaptive and self._floor is not None:
            threshold = max(self.threshold, self._floor * self.margin)
        if level < threshold:
            if self.adaptive:
                self._floor = level if self._floor is None else (
                    self.smoothing * self._floor + (1 - self.smoothing) * level)
            return [0.0] * len(frame), False
        return list(frame), True


class NoiseReducer:
    """High-pass then gate. Returns (frame, is_speech)."""

    def __init__(self, gate=None, highpass=None):
        self.gate = gate or NoiseGate()
        self.highpass = highpass or HighPass()

    def process(self, frame):
        return self.gate.process(self.highpass.process(frame))
