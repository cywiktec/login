import json
import os
import tempfile
from pathlib import Path

from .state_manager import GuardianState


class SnapshotManager:
    def __init__(self, snapshot_path):
        self.snapshot_path = Path(snapshot_path)

    def save(self, state_manager):
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_path = tempfile.mkstemp(
            dir=self.snapshot_path.parent,
            prefix=f".{self.snapshot_path.name}.",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as snapshot_file:
                json.dump({"state": state_manager.state.value}, snapshot_file)
                snapshot_file.flush()
                os.fsync(snapshot_file.fileno())
            os.replace(temporary_path, self.snapshot_path)
        except BaseException:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            raise

    def restore(self, state_manager):
        with self.snapshot_path.open(encoding="utf-8") as snapshot_file:
            snapshot = json.load(snapshot_file)
        state_manager.restore_state(GuardianState(snapshot["state"]))
