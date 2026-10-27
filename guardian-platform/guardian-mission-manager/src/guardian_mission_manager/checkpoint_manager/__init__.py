"""Atomic JSON checkpoints of mission progress."""

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Checkpoint:
    mission_id: str
    state: str
    next_step: int
    plan_steps: list


class CheckpointManager:
    def __init__(self, directory):
        self.directory = Path(directory)

    def _path(self, mission_id):
        if Path(mission_id).name != mission_id or mission_id in ("", ".", ".."):
            raise ValueError("invalid mission id")
        return self.directory / f"{mission_id}.json"

    def save(self, checkpoint):
        path = self._path(checkpoint.mission_id)
        self.directory.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.directory, prefix=f".{path.name}.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(asdict(checkpoint), handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise

    def load(self, mission_id):
        """Return the checkpoint, or None if there is none."""
        try:
            with self._path(mission_id).open(encoding="utf-8") as handle:
                return Checkpoint(**json.load(handle))
        except FileNotFoundError:
            return None

    def delete(self, mission_id):
        self._path(mission_id).unlink(missing_ok=True)

    def list_ids(self):
        if not self.directory.exists():
            return []
        return sorted(p.stem for p in self.directory.glob("*.json"))
