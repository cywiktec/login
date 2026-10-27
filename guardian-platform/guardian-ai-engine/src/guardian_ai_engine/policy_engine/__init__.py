"""Deny-by-default policy: decides whether an intent may run in the current state."""

from dataclasses import dataclass

from ..intent_parser import INTENTS

READ_ONLY = {"report_status", "battery_level", "run_diagnostics", "detect_motion"}
# Never accepted from an LLM; needs an explicit operator phrase.
RULE_ONLY = {"recover"}

# Guardian states from guardian-core. Anything else (including None) matches nothing.
ALLOWED_STATES = {
    "start_patrol": {"READY"},
    "return_to_base": {"READY", "MISSION"},
    "abort_mission": {"MISSION"},
    "take_snapshot": {"READY", "MISSION", "RTB", "CHARGING", "SAFE_MODE"},
    "recover": {"INIT", "READY", "SAFE_MODE", "EMERGENCY_STOP"},
    "start_charging": {"READY", "RTB"},
    "enter_safe_mode": {"READY"},
}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


class PolicyEngine:
    def __init__(self, llm_min_confidence=0.8):
        self.llm_min_confidence = llm_min_confidence

    def evaluate(self, intent, state):
        if intent.name not in INTENTS:
            return Decision(False, f"unknown intent {intent.name!r}")
        # Stopping is always allowed, from any source and state.
        if intent.name == "emergency_stop":
            return Decision(True, "emergency stop is always allowed")
        if intent.source not in ("rule", "llm"):
            return Decision(False, f"untrusted source {intent.source!r}")
        if intent.name in RULE_ONLY and intent.source != "rule":
            return Decision(False, f"{intent.name} requires an explicit operator command")
        if intent.name in READ_ONLY:
            return Decision(True, "read-only")
        if intent.source == "llm" and intent.confidence < self.llm_min_confidence:
            return Decision(False, f"confidence {intent.confidence:.2f} below {self.llm_min_confidence}")
        if state not in ALLOWED_STATES.get(intent.name, set()):
            return Decision(False, f"{intent.name} is not allowed in state {state!r}")
        return Decision(True, "allowed")
