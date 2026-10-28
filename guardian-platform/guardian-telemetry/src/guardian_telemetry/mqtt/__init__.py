"""MQTT-style topics and an in-memory broker (no network, no real MQTT client)."""

from ..message import KINDS, ROBOT_ID, MessageError, make_message, parse_message

PREFIX = "guardian"


def topic_for(robot_id, kind):
    if not ROBOT_ID.match(robot_id) or kind not in KINDS:
        raise MessageError("bad robot id or kind")
    return f"{PREFIX}/{robot_id}/{kind}"


def parse_topic(topic):
    """Returns (robot_id, kind) or raises MessageError. Wildcards are not valid in publish topics."""
    parts = topic.split("/")
    if len(parts) != 3 or parts[0] != PREFIX or not ROBOT_ID.match(parts[1]) or parts[2] not in KINDS:
        raise MessageError(f"bad topic {topic!r}")
    return parts[1], parts[2]


def topic_matches(pattern, topic):
    """MQTT wildcard rules: '+' matches one level, '#' (last only) matches the rest."""
    p, t = pattern.split("/"), topic.split("/")
    for i, level in enumerate(p):
        if level == "#":
            return i == len(p) - 1
        if i >= len(t) or (level != "+" and level != t[i]):
            return False
    return len(p) == len(t)


class InMemoryBroker:
    def __init__(self):
        self._subs = []  # (pattern, callback)
        self.rejected = 0

    def subscribe(self, pattern, callback):
        self._subs.append((pattern, callback))

    def publish(self, topic, payload):
        """Validates topic and payload, and that they agree. Returns the number of deliveries.
        A broken subscriber never blocks the others."""
        try:
            robot_id, kind = parse_topic(topic)
            msg = parse_message(payload)
            if (msg.robot_id, msg.kind) != (robot_id, kind):
                raise MessageError("topic does not match payload")
        except MessageError:
            self.rejected += 1
            return 0
        delivered = 0
        for pattern, callback in list(self._subs):
            if topic_matches(pattern, topic):
                try:
                    callback(topic, msg)
                    delivered += 1
                except Exception:
                    pass
        return delivered

    def publish_message(self, msg):
        return self.publish(topic_for(msg.robot_id, msg.kind), msg.to_bytes())
