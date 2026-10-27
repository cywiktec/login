import unittest

from guardian_core.state_manager import (
    GuardianState,
    InvalidTransition,
    StateManager,
)


def manager_in(*path):
    manager = StateManager()
    for state in path:
        manager.change_state(state)
    return manager


class StateManagerTests(unittest.TestCase):
    def test_startup_sequence(self):
        manager = manager_in(GuardianState.SELF_TEST, GuardianState.READY)
        self.assertIs(manager.state, GuardianState.READY)

    def test_ready_branches(self):
        for target in (
            GuardianState.MISSION,
            GuardianState.RTB,
            GuardianState.CHARGING,
            GuardianState.SAFE_MODE,
        ):
            manager = manager_in(GuardianState.SELF_TEST, GuardianState.READY)
            manager.change_state(target)
            self.assertIs(manager.state, target)

    def test_safe_mode_leads_to_emergency_stop(self):
        manager = manager_in(
            GuardianState.SELF_TEST, GuardianState.READY, GuardianState.SAFE_MODE
        )
        manager.change_state(GuardianState.EMERGENCY_STOP)
        self.assertIs(manager.state, GuardianState.EMERGENCY_STOP)

    def test_emergency_stop_from_any_state_and_terminal(self):
        manager = manager_in(GuardianState.SELF_TEST, GuardianState.READY,
                             GuardianState.MISSION)
        manager.change_state(GuardianState.EMERGENCY_STOP)
        with self.assertRaises(InvalidTransition):
            manager.change_state(GuardianState.READY)

    def test_invalid_transitions_rejected(self):
        manager = StateManager()
        with self.assertRaises(InvalidTransition):
            manager.change_state(GuardianState.READY)
        self.assertIs(manager.state, GuardianState.INIT)

    def test_state_property_is_read_only(self):
        with self.assertRaises(AttributeError):
            StateManager().state = GuardianState.READY
