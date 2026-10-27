"""Transport abstraction between the driver and the robot's DDS network.

A real implementation (e.g. wrapping the Unitree SDK) must provide the same
interface. Only InMemoryTransport exists here; nothing has been run on a robot.
"""

import threading
from collections import defaultdict

# Placeholder topic names: verify against the robot's SDK before use.
TOPIC_LOW_STATE = "rt/lowstate"
TOPIC_SPORT_STATE = "rt/sportmodestate"
TOPIC_SPORT_REQUEST = "rt/api/sport/request"


class Transport:
    def publish(self, topic, message):
        raise NotImplementedError

    def subscribe(self, topic, callback):
        raise NotImplementedError

    def close(self):
        pass


class InMemoryTransport(Transport):
    """Loopback transport for tests and simulation."""

    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers = defaultdict(list)
        self.published = []
        self.closed = False

    def publish(self, topic, message):
        if self.closed:
            raise ConnectionError("transport is closed")
        with self._lock:
            self.published.append((topic, message))
            callbacks = list(self._subscribers[topic])
        for callback in callbacks:
            callback(message)

    def subscribe(self, topic, callback):
        with self._lock:
            self._subscribers[topic].append(callback)

    def close(self):
        self.closed = True


class DdsBridge:
    def __init__(self, transport):
        self.transport = transport

    def send_sport_request(self, request):
        self.transport.publish(TOPIC_SPORT_REQUEST, request)

    def on_low_state(self, callback):
        self.transport.subscribe(TOPIC_LOW_STATE, callback)

    def on_sport_state(self, callback):
        self.transport.subscribe(TOPIC_SPORT_STATE, callback)

    def close(self):
        self.transport.close()
