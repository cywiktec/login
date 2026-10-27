"""App core: API transport abstraction and command sending with confirmation.

Commands are phrases ("MISIEK, wróć do bazy.") that the robot's own parser and policy
decide on. The app only avoids accidents and never reports a command as done unless the
robot said so.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from ..alerts import AlertInbox
from ..settings import Settings
from ..telemetry import TelemetryView

# Need confirmation when settings.confirm_commands is on. Stop is never listed here.
ACTUATING = {"rozpocznij patrol", "wroc do bazy", "zatrzymaj misje", "wznow po awarii"}


class Transport:
    def send(self, path, payload=None):
        """Return a dict reply or raise on network failure."""
        raise NotImplementedError


class FakeTransport(Transport):
    def __init__(self, replies=None, fail=False):
        self.replies = replies or {}
        self.fail = fail
        self.sent = []

    def send(self, path, payload=None):
        self.sent.append((path, payload))
        if self.fail:
            raise ConnectionError("offline")
        return self.replies.get(path, {"ok": True})


@dataclass(frozen=True)
class CommandOutcome:
    status: str  # sent, needs_confirmation, rejected, offline, error
    detail: str = ""
    reply: Optional[dict] = None


def _plain(command):
    text = unicodedata.normalize("NFKD", command.lower().replace("ł", "l"))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"^misiek\s*[,:]?\s*", "", text.strip())
    return text.strip(" .!")


class GuardianApp:
    def __init__(self, transport, settings=None, telemetry=None, alerts=None):
        self.transport = transport
        self.settings = settings or Settings()
        self.telemetry = telemetry or TelemetryView(self.settings.get("stale_after_s"))
        self.alerts = alerts or AlertInbox()
        self._pending = None

    def send_command(self, command, confirmed=False):
        plain = _plain(command)
        if not plain:
            return CommandOutcome("rejected", "empty command")
        if self.settings.get("confirm_commands") and plain in ACTUATING and not confirmed:
            self._pending = command
            return CommandOutcome("needs_confirmation", plain)
        self._pending = None
        return self._post("/command", {"text": command})

    def confirm_pending(self):
        if self._pending is None:
            return CommandOutcome("rejected", "nothing to confirm")
        return self.send_command(self._pending, confirmed=True)

    def cancel_pending(self):
        self._pending = None

    def emergency_stop(self):
        """Always sent immediately, even when telemetry is stale. No confirmation."""
        return self._post("/command", {"text": "MISIEK, stop"})

    def submit_mission(self, draft):
        try:
            payload = draft.to_payload()
        except ValueError as error:
            return CommandOutcome("rejected", str(error))
        return self._post("/missions", payload)

    def refresh(self):
        try:
            data = self.transport.send("/telemetry")
        except Exception:
            return False
        return self.telemetry.update(data)

    def _post(self, path, payload):
        try:
            reply = self.transport.send(path, payload)
        except ConnectionError as error:
            return CommandOutcome("offline", str(error))
        except Exception as error:
            return CommandOutcome("error", f"{type(error).__name__}: {error}")
        if not isinstance(reply, dict) or reply.get("ok") is not True:
            detail = reply.get("error", "robot rejected") if isinstance(reply, dict) else "bad reply"
            return CommandOutcome("rejected", str(detail), reply if isinstance(reply, dict) else None)
        return CommandOutcome("sent", "", reply)
