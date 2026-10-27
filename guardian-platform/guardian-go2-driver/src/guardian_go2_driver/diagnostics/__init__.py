"""Driver self-diagnostics."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


class Diagnostics:
    def __init__(self, transport, collector, controller, max_age=2.0):
        self.transport = transport
        self.collector = collector
        self.controller = controller
        self.max_age = max_age

    def run(self):
        results = []
        closed = getattr(self.transport, "closed", False)
        results.append(CheckResult("transport", not closed, "closed" if closed else "open"))

        fresh = self.collector.latest(self.max_age)
        results.append(
            CheckResult("telemetry", fresh is not None,
                        "fresh" if fresh else f"none within {self.max_age}s")
        )
        if self.collector.rejected:
            results.append(
                CheckResult("telemetry_quality", False, f"{self.collector.rejected} malformed messages")
            )
        results.append(
            CheckResult("control", not self.controller.latched,
                        "latched (emergency stop)" if self.controller.latched else "ready")
        )
        return results

    def healthy(self):
        return all(r.ok for r in self.run())
