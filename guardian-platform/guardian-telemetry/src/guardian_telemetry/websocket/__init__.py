"""Fan-out hub for dashboard clients. Slow clients lose old messages; they never block the robot.

Pure logic: it has no sockets and implements no WebSocket protocol.
"""

from collections import deque


class Client:
    def __init__(self, robot_ids=None, kinds=None, max_queue=100):
        self.robot_ids = set(robot_ids) if robot_ids else None
        self.kinds = set(kinds) if kinds else None
        self._queue = deque(maxlen=max_queue)
        self.dropped = 0
        self.closed = False

    def wants(self, msg):
        return ((self.robot_ids is None or msg.robot_id in self.robot_ids)
                and (self.kinds is None or msg.kind in self.kinds))

    def offer(self, msg):
        if len(self._queue) == self._queue.maxlen:
            self.dropped += 1  # deque drops the oldest
        self._queue.append(msg)

    def drain(self):
        items = list(self._queue)
        self._queue.clear()
        return items


class Hub:
    def __init__(self, max_clients=100):
        self.max_clients = max_clients
        self._clients = []

    def connect(self, **filters):
        """Returns a Client, or None when the hub is full."""
        if len(self._clients) >= self.max_clients:
            return None
        client = Client(**filters)
        self._clients.append(client)
        return client

    def disconnect(self, client):
        client.closed = True
        if client in self._clients:
            self._clients.remove(client)

    def broadcast(self, msg):
        n = 0
        for client in self._clients:
            if client.wants(msg):
                client.offer(msg)
                n += 1
        return n

    def __len__(self):
        return len(self._clients)
