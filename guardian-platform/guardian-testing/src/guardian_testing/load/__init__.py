"""Small load harness: run a callable many times, optionally from several threads."""

import math
import threading
import time
from dataclasses import dataclass, field
from typing import List


def percentile(values, p):
    """Nearest-rank percentile; 0 for no data."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[rank - 1]


@dataclass
class LoadResult:
    count: int
    errors: int
    elapsed_s: float
    durations: List[float] = field(default_factory=list)

    @property
    def error_rate(self):
        return self.errors / self.count if self.count else 1.0

    @property
    def throughput(self):
        return self.count / self.elapsed_s if self.elapsed_s > 0 else 0.0

    def p(self, pct):
        return percentile(self.durations, pct)


def run_load(fn, iterations, threads=1, clock=time.perf_counter):
    """Call fn(i) `iterations` times split across `threads`. Exceptions count as errors."""
    if iterations < 1 or threads < 1:
        raise ValueError("iterations and threads must be at least 1")
    durations, errors, lock = [], [0], threading.Lock()

    def worker(indices):
        local, bad = [], 0
        for i in indices:
            start = clock()
            try:
                fn(i)
            except Exception:
                bad += 1
            local.append(clock() - start)
        with lock:
            durations.extend(local)
            errors[0] += bad

    chunks = [range(t, iterations, threads) for t in range(threads)]
    start = clock()
    pool = [threading.Thread(target=worker, args=(c,)) for c in chunks]
    for t in pool:
        t.start()
    for t in pool:
        t.join()
    return LoadResult(iterations, errors[0], clock() - start, durations)


def violations(result, max_error_rate=0.0, max_p99_s=None, min_throughput=None):
    """Human-readable list of violated thresholds; empty means the load test passed."""
    out = []
    if result.error_rate > max_error_rate:
        out.append(f"error rate {result.error_rate:.3f} > {max_error_rate}")
    if max_p99_s is not None and result.p(99) > max_p99_s:
        out.append(f"p99 {result.p(99):.4f}s > {max_p99_s}s")
    if min_throughput is not None and result.throughput < min_throughput:
        out.append(f"throughput {result.throughput:.1f}/s < {min_throughput}/s")
    return out
