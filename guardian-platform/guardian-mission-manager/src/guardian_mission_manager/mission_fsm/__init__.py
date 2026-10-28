"""Mission lifecycle state machine."""

from enum import Enum


class MissionState(Enum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    FAILED = "FAILED"


TERMINAL = {MissionState.COMPLETED, MissionState.ABORTED, MissionState.FAILED}

ALLOWED = {
    MissionState.PLANNED: {MissionState.RUNNING, MissionState.ABORTED},
    MissionState.RUNNING: {
        MissionState.PAUSED,
        MissionState.COMPLETED,
        MissionState.ABORTED,
        MissionState.FAILED,
    },
    MissionState.PAUSED: {MissionState.RUNNING, MissionState.ABORTED, MissionState.FAILED},
    MissionState.COMPLETED: set(),
    MissionState.ABORTED: set(),
    MissionState.FAILED: set(),
}


class InvalidMissionTransition(ValueError):
    pass


class MissionFSM:
    def __init__(self, state=MissionState.PLANNED):
        self._state = state

    @property
    def state(self):
        return self._state

    @property
    def finished(self):
        return self._state in TERMINAL

    def transition(self, new_state):
        if new_state not in ALLOWED[self._state]:
            raise InvalidMissionTransition(
                f"{self._state.value} -> {new_state.value} is not allowed"
            )
        self._state = new_state
        return new_state
