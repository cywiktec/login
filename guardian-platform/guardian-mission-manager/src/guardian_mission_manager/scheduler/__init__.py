"""Priority scheduler with injectable time."""

import heapq
import itertools
import time


class Scheduler:
    def __init__(self, clock=time.time):
        self._clock = clock
        self._heap = []
        self._counter = itertools.count()
        self._cancelled = set()

    def schedule(self, mission_id, start_at, priority=0):
        """Lower priority numbers run first among missions that are due."""
        self._cancelled.discard(mission_id)
        heapq.heappush(self._heap, (start_at, priority, next(self._counter), mission_id))

    def cancel(self, mission_id):
        self._cancelled.add(mission_id)

    def pop_due(self):
        """Return ids of all due missions, ordered by (priority, start time, insertion)."""
        now = self._clock()
        due = []
        while self._heap and self._heap[0][0] <= now:
            start_at, priority, order, mission_id = heapq.heappop(self._heap)
            if mission_id in self._cancelled:
                continue
            due.append((priority, start_at, order, mission_id))
        return [item[3] for item in sorted(due)]

    def pending(self):
        return sum(1 for entry in self._heap if entry[3] not in self._cancelled)
