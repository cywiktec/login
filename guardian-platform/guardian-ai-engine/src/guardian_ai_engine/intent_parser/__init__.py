"""Turn operator text into an Intent: deterministic rules first, optional LLM fallback."""

import re
import unicodedata
from dataclasses import dataclass

from ..llm_connector import classify

UNKNOWN = "unknown"
MAX_TEXT = 500

# Intent names; state and source rules for each live in policy_engine.
INTENTS = (
    "report_status",
    "battery_level",
    "start_patrol",
    "return_to_base",
    "abort_mission",
    "run_diagnostics",
    "take_snapshot",
    "recover",
    "start_charging",
    "enter_safe_mode",
    "emergency_stop",
    "detect_motion",
)

_PHRASES = {
    "raport stanu": "report_status",
    "status": "report_status",
    "poziom baterii": "battery_level",
    "raport baterii": "battery_level",
    "wykryj ruch": "detect_motion",
    "rozpocznij patrol": "start_patrol",
    "misja": "start_patrol",
    "wroc do bazy": "return_to_base",
    "rtb": "return_to_base",
    "zatrzymaj misje": "abort_mission",
    "uruchom diagnostyke": "run_diagnostics",
    "wykonaj snapshot": "take_snapshot",
    "wznow po awarii": "recover",
    "ladowanie": "start_charging",
    "safe": "enter_safe_mode",
    "stop": "emergency_stop",
}


@dataclass(frozen=True)
class Intent:
    name: str
    source: str = "rule"  # "rule", "llm" or "none"
    confidence: float = 1.0
    raw: str = ""


def normalize(text):
    text = text.lower().replace("ł", "l")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"^misiek\s*[,:]?\s*", "", text.strip())
    return text.strip(" .!")


class IntentParser:
    def __init__(self, llm=None, min_confidence=0.6):
        self.llm = llm
        self.min_confidence = min_confidence

    def parse(self, text):
        raw = str(text)[:MAX_TEXT]
        name = _PHRASES.get(normalize(raw))
        if name:
            return Intent(name, "rule", 1.0, raw)

        if self.llm is not None:
            result = classify(self.llm, raw, INTENTS)
            if result and result[1] >= self.min_confidence:
                return Intent(result[0], "llm", result[1], raw)
        return Intent(UNKNOWN, "none", 0.0, raw)
