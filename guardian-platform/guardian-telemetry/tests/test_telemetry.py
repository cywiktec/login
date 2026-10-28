import os
import tempfile
import unittest

from guardian_telemetry.dds import Domain, Topic, normalize_sample
from guardian_telemetry.event_store import EventStore
from guardian_telemetry.message import MAX_PAYLOAD_BYTES, MessageError, make_message, parse_message
from guardian_telemetry.mqtt import InMemoryBroker, parse_topic, topic_for, topic_matches
from guardian_telemetry.snapshots import SnapshotCache
from guardian_telemetry.websocket import Hub


def msg(robot="go2-01", kind="battery", ts=1.0, **data):
    return make_message(robot, kind, ts, data or {"pct": 80})


class MessageTests(unittest.TestCase):
    def test_roundtrip(self):
        m = msg()
        self.assertEqual(parse_message(m.to_bytes()), m)

    def test_rejects_bad(self):
        for args in [("Bad ID", "battery", 1, {}), ("a", "nope", 1, {}), ("a", "battery", "1", {}),
                     ("a", "battery", float("nan"), {}), ("a", "battery", True, {}),
                     ("a", "battery", 1, []), ("a", "battery", 1, {"x": float("inf")}),
                     ("a", "battery", 1, {"x": "y" * MAX_PAYLOAD_BYTES}), ("../x", "battery", 1, {})]:
            with self.assertRaises((MessageError, ValueError), msg=args):
                make_message(*args)

    def test_parse_rejects_bad(self):
        for raw in (b"", b"{", b"[]", b'{"robot_id": "a"}', None, b"x" * (MAX_PAYLOAD_BYTES + 1),
                    b'{"robot_id":"a","kind":"battery","ts":NaN,"data":{}}'):
            with self.assertRaises(MessageError):
                parse_message(raw)


class MqttTests(unittest.TestCase):
    def test_topics(self):
        self.assertEqual(topic_for("go2-01", "battery"), "guardian/go2-01/battery")
        self.assertEqual(parse_topic("guardian/go2-01/pose"), ("go2-01", "pose"))
        for bad in ("guardian/+/pose", "guardian/a/pose/x", "other/a/pose", "guardian/a/nope", "#"):
            with self.assertRaises(MessageError):
                parse_topic(bad)

    def test_wildcards(self):
        self.assertTrue(topic_matches("guardian/+/battery", "guardian/a/battery"))
        self.assertTrue(topic_matches("guardian/#", "guardian/a/battery"))
        self.assertFalse(topic_matches("guardian/+", "guardian/a/battery"))
        self.assertFalse(topic_matches("guardian/#/x", "guardian/a/x"))
        self.assertFalse(topic_matches("guardian/a/battery", "guardian/a"))

    def test_broker_delivery_and_isolation(self):
        broker = InMemoryBroker()
        got = []
        broker.subscribe("guardian/+/battery", lambda t, m: (_ for _ in ()).throw(RuntimeError("bad")))
        broker.subscribe("guardian/#", lambda t, m: got.append(m))
        self.assertEqual(broker.publish_message(msg()), 1)  # first subscriber raised
        self.assertEqual(len(got), 1)

    def test_broker_rejects_mismatch_and_garbage(self):
        broker = InMemoryBroker()
        self.assertEqual(broker.publish("guardian/a/battery", msg(robot="b").to_bytes()), 0)
        self.assertEqual(broker.publish("guardian/a/battery", b"junk"), 0)
        self.assertEqual(broker.rejected, 2)


class DdsTests(unittest.TestCase):
    def test_keep_last_and_late_joiner(self):
        t = Topic("battery", depth=2)
        for i in range(4):
            t.write({"i": i})
        seen = []
        t.subscribe(seen.append)
        self.assertEqual(seen, [{"i": 2}, {"i": 3}])
        t.write({"i": 4})
        self.assertEqual(seen[-1], {"i": 4})
        with self.assertRaises(ValueError):
            Topic("x", depth=0)

    def test_domain_reuses_topics(self):
        d = Domain()
        self.assertIs(d.topic("a"), d.topic("a"))

    def test_normalize(self):
        m = normalize_sample({"pct": 50, "stamp": 12.5}, "go2-01", "battery", lambda: 99.0)
        self.assertEqual((m.ts, m.data), (12.5, {"pct": 50}))
        self.assertEqual(normalize_sample({"pct": 1}, "go2-01", "battery", lambda: 99.0).ts, 99.0)
        self.assertIsNone(normalize_sample("x", "go2-01", "battery", lambda: 1.0))
        self.assertIsNone(normalize_sample({"pct": 1}, "BAD", "battery", lambda: 1.0))


class HubTests(unittest.TestCase):
    def test_filters(self):
        hub = Hub()
        a = hub.connect(robot_ids=["go2-01"])
        b = hub.connect(kinds=["pose"])
        self.assertEqual(hub.broadcast(msg()), 1)
        self.assertEqual((len(a.drain()), len(b.drain())), (1, 0))

    def test_slow_client_drops_oldest(self):
        hub = Hub()
        c = hub.connect(max_queue=2)
        for i in range(5):
            hub.broadcast(msg(ts=float(i)))
        self.assertEqual([m.ts for m in c.drain()], [3.0, 4.0])
        self.assertEqual(c.dropped, 3)

    def test_limits_and_disconnect(self):
        hub = Hub(max_clients=1)
        c = hub.connect()
        self.assertIsNone(hub.connect())
        hub.disconnect(c)
        self.assertTrue(c.closed)
        self.assertEqual(len(hub), 0)


class SnapshotTests(unittest.TestCase):
    def test_latest_and_staleness(self):
        now = [100.0]
        cache = SnapshotCache(clock=lambda: now[0])
        self.assertTrue(cache.update(msg(ts=10)))
        self.assertFalse(cache.update(msg(ts=5, pct=1)))  # older message ignored
        self.assertEqual(cache.get("go2-01", "battery").data, {"pct": 80})
        now[0] = 120.0
        self.assertIsNotNone(cache.get("go2-01", "battery"))
        self.assertIsNone(cache.get("go2-01", "battery", max_age=5))
        self.assertEqual(cache.snapshot("go2-01", max_age=5), {})
        self.assertEqual(cache.robots(), ["go2-01"])
        self.assertIsNone(cache.get("x", "pose"))


class EventStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = os.path.join(self._tmp.name, "sub", "events.jsonl")

    def test_append_query(self):
        s = EventStore(self.path)
        for i in range(5):
            self.assertTrue(s.append(msg(ts=float(i), kind="event" if i % 2 else "battery")))
        self.assertEqual(len(s.query()), 5)
        self.assertEqual([m.ts for m in s.query(kind="event")], [1.0, 3.0])
        self.assertEqual([m.ts for m in s.query(since=1, until=3)], [1.0, 2.0, 3.0])
        self.assertEqual(len(s.query(limit=2)), 2)
        self.assertEqual(s.query(robot_id="other"), [])
        self.assertEqual(s.query(limit=0), [])

    def test_corrupt_lines_skipped(self):
        s = EventStore(self.path)
        s.append(msg(ts=1.0))
        with open(self.path, "ab") as f:
            f.write(b"garbage\n")
            f.write(b'{"robot_id": "a", "kind": "nope", "ts": 1, "data": {}}\n')
        s.append(msg(ts=2.0))
        self.assertEqual(len(s.query()), 2)
        self.assertEqual(s.skipped, 2)

    def test_full_store_refuses(self):
        s = EventStore(self.path, max_bytes=100)
        self.assertTrue(s.append(msg()))
        self.assertFalse(s.append(msg(ts=2.0)))
        self.assertEqual(len(s.query()), 1)

    def test_empty(self):
        self.assertEqual(EventStore(self.path).query(), [])


if __name__ == "__main__":
    unittest.main()
