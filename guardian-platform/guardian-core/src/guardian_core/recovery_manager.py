class RecoveryManager:
    def __init__(self, snapshot_manager, state_manager):
        self.snapshot_manager = snapshot_manager
        self.state_manager = state_manager

    def recover(self):
        self.snapshot_manager.restore(self.state_manager)
