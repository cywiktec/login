from enum import Enum


class GuardianState(Enum):
    INIT = "INIT"
    SELF_TEST = "SELF_TEST"
    READY = "READY"
    MISSION = "MISSION"
    RTB = "RTB"
    CHARGING = "CHARGING"
    SAFE_MODE = "SAFE_MODE"
    EMERGENCY_STOP = "EMERGENCY_STOP"


# EMERGENCY_STOP is additionally reachable from every state.
ALLOWED_TRANSITIONS = {
    GuardianState.INIT: {GuardianState.SELF_TEST},
    GuardianState.SELF_TEST: {GuardianState.READY},
    GuardianState.READY: {
        GuardianState.MISSION,
        GuardianState.RTB,
        GuardianState.CHARGING,
        GuardianState.SAFE_MODE,
    },
    GuardianState.MISSION: {GuardianState.RTB, GuardianState.READY},
    GuardianState.RTB: {GuardianState.CHARGING, GuardianState.READY},
    GuardianState.CHARGING: {GuardianState.READY},
    GuardianState.SAFE_MODE: {GuardianState.EMERGENCY_STOP},
    GuardianState.EMERGENCY_STOP: set(),
}


class InvalidTransition(ValueError):
    pass


class StateManager:
    def __init__(self):
        self._state = GuardianState.INIT

    @property
    def state(self):
        return self._state

    def can_change_to(self, new_state: GuardianState):
        return (
            new_state is GuardianState.EMERGENCY_STOP
            and self._state is not GuardianState.EMERGENCY_STOP
        ) or new_state in ALLOWED_TRANSITIONS[self._state]

    def change_state(self, new_state: GuardianState):
        if not isinstance(new_state, GuardianState):
            raise TypeError("new_state must be a GuardianState")
        if not self.can_change_to(new_state):
            raise InvalidTransition(
                f"{self._state.value} -> {new_state.value} is not allowed"
            )

        old_state = self._state
        self._state = new_state
        print(f"[STATE] {old_state.value} -> {new_state.value}")

    def restore_state(self, state: GuardianState):
        if not isinstance(state, GuardianState):
            raise TypeError("state must be a GuardianState")

        old_state = self._state
        self._state = state
        print(f"[STATE] restored {old_state.value} -> {state.value}")
