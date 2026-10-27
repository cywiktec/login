"""Expand an intent into the ordered intents that should run."""

from dataclasses import replace

from ..intent_parser import Intent


class Planner:
    def plan(self, intent):
        """Patrols are preceded by diagnostics. Sub-intents keep the original source,
        so planning can never raise an intent's trust level."""
        if intent.name == "start_patrol":
            return [replace(intent, name="run_diagnostics"), intent]
        return [intent]
