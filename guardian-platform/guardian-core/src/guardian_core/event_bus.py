from collections import defaultdict


class EventBus:
    def __init__(self):
        self.subscribers = defaultdict(list)

    def subscribe(self, event_name, callback):
        self.subscribers[event_name].append(callback)

    def publish(self, event_name, data=None):
        if event_name not in self.subscribers:
            return

        for callback in self.subscribers[event_name]:
            callback(data)
