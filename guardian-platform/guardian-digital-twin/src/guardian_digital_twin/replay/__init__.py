"""Trace recording and replay (JSONL). A corrupt trace is an error, never silently skipped."""

import json
import math
import os

KEYS = ("t", "x", "y", "battery", "estopped")


class TraceError(ValueError):
    pass


def save(path, trace):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for state in trace:
            f.write(json.dumps(state, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _check(state, lineno):
    if not isinstance(state, dict) or any(k not in state for k in KEYS):
        raise TraceError(f"line {lineno}: missing keys")
    for k in ("t", "x", "y", "battery"):
        v = state[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise TraceError(f"line {lineno}: bad {k}")
    if not isinstance(state["estopped"], bool):
        raise TraceError(f"line {lineno}: bad estopped")


def load(path):
    trace = []
    with open(path, encoding="utf-8") as f:
        for no, line in enumerate(f, 1):
            try:
                state = json.loads(line)
            except ValueError as exc:
                raise TraceError(f"line {no}: invalid JSON") from exc
            _check(state, no)
            if trace and state["t"] <= trace[-1]["t"]:
                raise TraceError(f"line {no}: time not increasing")
            trace.append(state)
    if not trace:
        raise TraceError("empty trace")
    return trace


def replay(trace, on_state):
    """Feeds states in order to the callback; returns the count."""
    for state in trace:
        on_state(state)
    return len(trace)


def diff(expected, actual, tol=1e-6):
    """Returns the index of the first differing state, or None when equal."""
    for i, (a, b) in enumerate(zip(expected, actual)):
        if a["estopped"] != b["estopped"] or any(abs(a[k] - b[k]) > tol for k in ("t", "x", "y", "battery")):
            return i
    if len(expected) != len(actual):
        return min(len(expected), len(actual))
    return None
