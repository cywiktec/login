"""DDS-style topics with KEEP_LAST history, and normalization of raw samples.

In-memory stand-in only. The real Go2 DDS transport lives in guardian-go2-driver.
"""

from collections import deque

from ..message import MessageError, make_message


class Topic:
    def __init__(self, name, depth=10):
        if depth < 1:
            raise ValueError("depth must be at least 1")
        self.name = name
        self._history = deque(maxlen=depth)
        self._readers = []

    def write(self, sample):
        self._history.append(sample)
        for reader in list(self._readers):
            try:
                reader(sample)
            except Exception:
                pass

    def read_history(self):
        return list(self._history)

    def subscribe(self, callback):
        """Late joiners get the retained history first (transient-local behaviour)."""
        for sample in list(self._history):
            callback(sample)
        self._readers.append(callback)


class Domain:
    def __init__(self):
        self._topics = {}

    def topic(self, name, depth=10):
        if name not in self._topics:
            self._topics[name] = Topic(name, depth)
        return self._topics[name]


def normalize_sample(sample, robot_id, kind, clock):
    """Wrap a raw dict sample from a DDS topic as a TelemetryMessage. Samples without a
    numeric 'stamp' are stamped with the local clock. Returns None for invalid samples."""
    if not isinstance(sample, dict):
        return None
    data = {k: v for k, v in sample.items() if k != "stamp"}
    stamp = sample.get("stamp")
    ts = stamp if isinstance(stamp, (int, float)) and not isinstance(stamp, bool) else clock()
    try:
        return make_message(robot_id, kind, ts, data)
    except MessageError:
        return None
