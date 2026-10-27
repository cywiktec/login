# guardian-ai-engine

Language understanding and command gating for MISIEK AI Guardian. Pure Python,
no dependencies. There is **no real LLM client**: `llm_connector` defines an
interface and a scripted `FakeLLM`; nothing here makes network calls and nothing
has been run against a model or the robot.

Pipeline: `IntentParser` → `Planner` → `CommandRouter` (asks `PolicyEngine`) → handlers.

| Module | Responsibility |
|---|---|
| `intent_parser` | Polish phrases to `Intent` by deterministic rules (same phrases as guardian-core); optional LLM fallback |
| `llm_connector` | `LLMConnector` interface, `FakeLLM`, prompt building, strict validation of LLM replies |
| `policy_engine` | Deny-by-default: allowed states per intent, LLM confidence floor, rule-only intents |
| `planner` | Expands an intent into ordered intents (patrol is preceded by diagnostics) |
| `command_router` | Evaluates policy, runs the handler, converts failures to results, logs to memory |
| `memory` | Bounded, thread-safe event log |

## Safety design

- LLM output is untrusted. It must be JSON naming a known intent with a confidence
  in [0, 1]; anything else, or any connector error, yields `unknown`.
- An LLM-sourced intent needs confidence >= 0.8 to actuate, and can never trigger
  `recover`; that requires an explicit operator phrase.
- `emergency_stop` is allowed from any source and state. Unknown states deny every
  non-read-only intent.
- Planning keeps the original source, so it cannot raise trust. A plan stops at
  the first step that does not execute; a handler returns `False` to signal failure.
- The router checks state through `state_provider` on every step, not once per plan.
- The policy is a second line of defense on top of guardian-core's own state
  machine and `guardian-safety-layer`, not a replacement for them.

## To do

- Real `LLMConnector` (with timeouts and rate limits) and handlers that call guardian-core.
- Intent parameters (route, loops); today intents carry none.
- The 0.8 / 0.6 confidence thresholds are untuned placeholders.

```
make test
```
