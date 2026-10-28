from .state_manager import GuardianState


class GuardianNode:
    def __init__(
        self,
        state_manager,
        watchdog,
        health_monitor,
        snapshot_manager=None,
        recovery_manager=None,
    ):
        self.state_manager = state_manager
        self.watchdog = watchdog
        self.health_monitor = health_monitor
        self.snapshot_manager = snapshot_manager
        self.recovery_manager = recovery_manager

    def initialize(self):
        self.state_manager.change_state(GuardianState.SELF_TEST)
        print("[GUARDIAN] self-test")
        self.state_manager.change_state(GuardianState.READY)

    def report_status(self):
        print("[STATUS]", self.state_manager.state.value)
        print(self.health_monitor.get_status())

    def start_mission(self):
        self.state_manager.change_state(GuardianState.MISSION)

    def return_to_base(self):
        self.state_manager.change_state(GuardianState.RTB)

    def start_charging(self):
        self.state_manager.change_state(GuardianState.CHARGING)

    def enter_safe_mode(self):
        self.state_manager.change_state(GuardianState.SAFE_MODE)

    def emergency_stop(self):
        self.state_manager.change_state(GuardianState.EMERGENCY_STOP)

    def abort_mission(self):
        if self.state_manager.state is not GuardianState.MISSION:
            print("[CMD] brak aktywnej misji")
            return
        self.state_manager.change_state(GuardianState.READY)

    def report_battery(self):
        battery = self.health_monitor.get_battery()
        if battery is None:
            print("[BATTERY] brak danych")
            return
        print(f"[BATTERY] {battery['percent']}% (ładowanie: {battery['plugged']})")

    def run_diagnostics(self):
        print("[DIAG] state:", self.state_manager.state.value)
        print("[DIAG] health:", self.health_monitor.get_status())
        print("[DIAG] battery:", self.health_monitor.get_battery())

    def take_snapshot(self):
        if self.snapshot_manager is None:
            print("[SNAPSHOT] niedostępny")
            return
        self.snapshot_manager.save(self.state_manager)
        print("[SNAPSHOT] zapisano")

    def recover(self):
        if self.recovery_manager is None:
            print("[RECOVERY] niedostępne")
            return
        try:
            self.recovery_manager.recover()
        except FileNotFoundError:
            print("[RECOVERY] brak snapshotu")
