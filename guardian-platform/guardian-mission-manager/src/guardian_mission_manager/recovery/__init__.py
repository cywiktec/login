"""Resume interrupted missions from checkpoints."""

from ..checkpoint_manager import Checkpoint
from ..mission_fsm import MissionState


class RecoveryManager:
    RESUMABLE = {MissionState.RUNNING.value, MissionState.PAUSED.value}

    def __init__(self, checkpoints):
        self.checkpoints = checkpoints

    def interrupted(self):
        """Ids of missions whose last checkpoint shows them still in progress."""
        result = []
        for mission_id in self.checkpoints.list_ids():
            checkpoint = self.checkpoints.load(mission_id)
            if checkpoint and checkpoint.state in self.RESUMABLE:
                result.append(mission_id)
        return result

    def resume(self, mission_id):
        """Return (checkpoint, remaining_steps) for an interrupted mission.

        The step that was in flight (``next_step``) is repeated, not skipped.
        """
        checkpoint = self.checkpoints.load(mission_id)
        if checkpoint is None:
            raise LookupError(f"no checkpoint for mission {mission_id!r}")
        if checkpoint.state not in self.RESUMABLE:
            raise ValueError(f"mission {mission_id!r} is {checkpoint.state}, not resumable")
        return checkpoint, checkpoint.plan_steps[checkpoint.next_step:]

    def mark_failed(self, mission_id):
        checkpoint = self.checkpoints.load(mission_id)
        if checkpoint is None:
            raise LookupError(f"no checkpoint for mission {mission_id!r}")
        self.checkpoints.save(
            Checkpoint(
                checkpoint.mission_id,
                MissionState.FAILED.value,
                checkpoint.next_step,
                checkpoint.plan_steps,
            )
        )
