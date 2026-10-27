"""Route policy-approved intents to handlers."""

from dataclasses import dataclass
from typing import Any

EXECUTED = "executed"
DENIED = "denied"
UNHANDLED = "unhandled"
FAILED = "failed"
ERROR = "error"


@dataclass(frozen=True)
class RouteResult:
    status: str
    intent: Any
    message: str = ""
    value: Any = None


class CommandRouter:
    def __init__(self, handlers, policy, state_provider, memory=None):
        """handlers: intent name -> callable. A handler returning False reports a failed
        precondition; any other return value counts as success."""
        self.handlers = dict(handlers)
        self.policy = policy
        self.state_provider = state_provider
        self.memory = memory

    def route(self, intent):
        try:
            state = self.state_provider()
        except Exception:
            state = None  # unknown state: only always-allowed intents pass

        decision = self.policy.evaluate(intent, state)
        if not decision.allowed:
            return self._finish(RouteResult(DENIED, intent, decision.reason))

        handler = self.handlers.get(intent.name)
        if handler is None:
            return self._finish(RouteResult(UNHANDLED, intent, "no handler registered"))

        try:
            value = handler()
        except Exception as error:
            return self._finish(RouteResult(ERROR, intent, f"{type(error).__name__}: {error}"))
        if value is False:
            return self._finish(RouteResult(FAILED, intent, "handler reported failure", value))
        return self._finish(RouteResult(EXECUTED, intent, "ok", value))

    def route_plan(self, intents):
        """Run in order; stop at the first intent that does not execute."""
        results = []
        for intent in intents:
            result = self.route(intent)
            results.append(result)
            if result.status != EXECUTED:
                break
        return results

    def _finish(self, result):
        if self.memory is not None:
            self.memory.remember(
                "command",
                {"intent": result.intent.name, "source": result.intent.source,
                 "status": result.status, "message": result.message},
            )
        return result
