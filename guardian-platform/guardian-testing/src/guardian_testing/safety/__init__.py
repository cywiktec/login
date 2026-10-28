"""Exhaustive invariant checks for the safety-critical rules. Each returns a list of violation
strings; an empty list means the invariants hold. They take the components as arguments so
that tests can also prove the checks catch a broken implementation."""

from guardian_ai_engine.intent_parser import INTENTS, Intent
from guardian_safety_layer.safety_fsm import SafetyFSM, SafetyLevel

STATES = ["INIT", "SELF_TEST", "READY", "MISSION", "RTB", "CHARGING", "SAFE_MODE", "EMERGENCY_STOP",
          None, "BOGUS"]
SOURCES = ("rule", "llm", "none", "web")
CONFIDENCES = (0.0, 0.5, 0.79, 0.8, 1.0)
READ_ONLY = {"report_status", "battery_level", "run_diagnostics", "detect_motion"}


def check_policy_invariants(policy):
    v = []
    for state in STATES:
        for source in SOURCES:
            for conf in CONFIDENCES:
                # Stopping must never be blocked.
                if not policy.evaluate(Intent("emergency_stop", source, conf), state).allowed:
                    v.append(f"emergency_stop denied (state={state}, source={source}, conf={conf})")
                # Nothing outside the known intents may pass.
                for name in ("unknown", "format_disk", ""):
                    if policy.evaluate(Intent(name, source, conf), state).allowed:
                        v.append(f"unknown intent {name!r} allowed")
                for name in INTENTS:
                    if name in READ_ONLY | {"emergency_stop"}:
                        continue
                    d = policy.evaluate(Intent(name, source, conf), state)
                    if d.allowed and source not in ("rule", "llm"):
                        v.append(f"{name} allowed from source {source!r}")
                    if d.allowed and state not in STATES[:8]:
                        v.append(f"{name} allowed in unknown state {state!r}")
                    if d.allowed and source == "llm" and name == "recover":
                        v.append("LLM-sourced recover allowed")
                    if d.allowed and source == "llm" and conf < 0.8:
                        v.append(f"low-confidence LLM {name} allowed")
    return v


def check_safety_fsm_invariants(make_fsm=SafetyFSM):
    v = []
    fsm = make_fsm()
    fsm.escalate(SafetyLevel.SAFE_MODE)
    fsm.escalate(SafetyLevel.WARNING)
    if fsm.level != SafetyLevel.SAFE_MODE:
        v.append("level went down on a lower escalation")
    fsm.escalate(SafetyLevel.EMERGENCY_STOP)
    try:
        fsm.reset()
        v.append("reset() cleared EMERGENCY_STOP")
    except PermissionError:
        pass
    if fsm.level != SafetyLevel.EMERGENCY_STOP:
        v.append("EMERGENCY_STOP lost after failed reset")
    return v
