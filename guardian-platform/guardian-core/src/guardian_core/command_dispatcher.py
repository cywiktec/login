import re
import unicodedata

from .state_manager import InvalidTransition


def normalize(command):
    text = command.lower().replace("ł", "l")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"^misiek\s*[,:]?\s*", "", text.strip())
    return text.strip(" .!")


class CommandDispatcher:
    def __init__(self, guardian):
        self.guardian = guardian
        g = guardian
        self._actions = {
            "raport stanu": g.report_status,
            "poziom baterii": g.report_battery,
            "rozpocznij patrol": g.start_mission,
            "misja": g.start_mission,
            "wroc do bazy": g.return_to_base,
            "rtb": g.return_to_base,
            "zatrzymaj misje": g.abort_mission,
            "uruchom diagnostyke": g.run_diagnostics,
            "wykonaj snapshot": g.take_snapshot,
            "wznow po awarii": g.recover,
            "ladowanie": g.start_charging,
            "safe": g.enter_safe_mode,
            "stop": g.emergency_stop,
        }

    def execute(self, command):
        action = self._actions.get(normalize(command))
        if action is None:
            print("[CMD] nierozpoznana komenda")
            return

        try:
            action()
        except InvalidTransition as error:
            print(f"[CMD] niedozwolone przejście: {error}")
