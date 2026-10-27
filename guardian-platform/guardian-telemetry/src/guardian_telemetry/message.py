"""Common telemetry message: validated, size-limited, JSON-serializable."""

import json
import math
import re
from dataclasses import dataclass

ROBOT_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
KINDS = {"state", "battery", "pose", "health", "event", "diagnostics"}
MAX_PAYLOAD_BYTES = 16 * 1024


class MessageError(ValueError):
    pass


@dataclass(frozen=True)
class TelemetryMessage:
    robot_id: str
    kind: str
    ts: float
    data: dict

    def to_bytes(self):
        raw = json.dumps({"robot_id": self.robot_id, "kind": self.kind, "ts": self.ts,
                          "data": self.data}, sort_keys=True, allow_nan=False).encode("utf-8")
        if len(raw) > MAX_PAYLOAD_BYTES:
            raise MessageError("payload too large")
        return raw


def make_message(robot_id, kind, ts, data):
    if not isinstance(robot_id, str) or not ROBOT_ID.match(robot_id):
        raise MessageError(f"bad robot id {robot_id!r}")
    if kind not in KINDS:
        raise MessageError(f"bad kind {kind!r}")
    if isinstance(ts, bool) or not isinstance(ts, (int, float)) or not math.isfinite(ts):
        raise MessageError("bad timestamp")
    if not isinstance(data, dict):
        raise MessageError("data must be an object")
    msg = TelemetryMessage(robot_id, kind, float(ts), data)
    msg.to_bytes()  # enforces JSON-serializable data and the size limit
    return msg


def parse_message(raw):
    """bytes/str -> TelemetryMessage. Raises MessageError for anything malformed."""
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if not isinstance(raw, (bytes, bytearray)) or len(raw) > MAX_PAYLOAD_BYTES:
        raise MessageError("payload missing or too large")
    try:
        obj = json.loads(raw)
    except ValueError as error:
        raise MessageError(f"invalid JSON: {error}") from error
    if not isinstance(obj, dict):
        raise MessageError("payload must be an object")
    try:
        return make_message(obj["robot_id"], obj["kind"], obj["ts"], obj["data"])
    except KeyError as error:
        raise MessageError(f"missing field {error}") from error
    except (TypeError, ValueError) as error:
        raise MessageError(str(error)) from error
