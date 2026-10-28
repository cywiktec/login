import unittest

from guardian_safety.state import SafetyManager, SafetyState, from_level
from guardian_safety_layer.safety_fsm import SafetyLevel


class State(unittest.TestCase):
    def test_initial(self):
        self.assertIs(SafetyManager().state, SafetyState.MONITORING)

    def test_escalation_order(self):
        m = SafetyManager()
        self.assertTrue(m.set_degraded("battery"))
        self.assertTrue(m.set_failsafe("lost input"))
        self.assertTrue(m.set_safe_mode())
        self.assertTrue(m.trigger_estop("operator"))
        self.assertEqual(len(m.history), 4)

    def test_no_downgrade(self):
        m = SafetyManager()
        m.trigger_estop()
        for call in (m.set_degraded, m.set_failsafe, m.set_safe_mode, m.trigger_estop):
            self.assertFalse(call())
        self.assertIs(m.state, SafetyState.E_STOP)

    def test_motion_allowed(self):
        m = SafetyManager()
        self.assertTrue(m.motion_allowed)
        m.set_degraded()
        self.assertTrue(m.motion_allowed)
        m.set_failsafe()
        self.assertFalse(m.motion_allowed)

    def test_clear_degraded_only(self):
        m = SafetyManager()
        m.set_degraded()
        self.assertTrue(m.clear_degraded())
        m.set_failsafe()
        self.assertFalse(m.clear_degraded())
        self.assertIs(m.state, SafetyState.FAILSAFE)

    def test_reset_guard(self):
        m = SafetyManager()
        m.trigger_estop()
        with self.assertRaises(PermissionError):
            m.reset()
        self.assertIs(m.state, SafetyState.E_STOP)
        m.allow_reset = True
        self.assertTrue(m.reset())
        self.assertIs(m.state, SafetyState.MONITORING)
        self.assertFalse(m.reset())

    def test_level_mapping(self):
        self.assertIs(from_level(SafetyLevel.NORMAL), SafetyState.MONITORING)
        self.assertIs(from_level(SafetyLevel.WARNING), SafetyState.DEGRADED)
        self.assertIs(from_level(SafetyLevel.SAFE_MODE), SafetyState.SAFE_MODE)
        self.assertIs(from_level(SafetyLevel.EMERGENCY_STOP), SafetyState.E_STOP)
        m = SafetyManager()
        self.assertTrue(m.apply_level(SafetyLevel.EMERGENCY_STOP))
        self.assertFalse(m.apply_level(SafetyLevel.NORMAL))

    def test_history_bounded(self):
        m = SafetyManager(allow_reset=True)
        for _ in range(600):
            m.set_degraded()
            m.reset()
        self.assertLessEqual(len(m.history), SafetyManager.MAX_HISTORY)


if __name__ == "__main__":
    unittest.main()
