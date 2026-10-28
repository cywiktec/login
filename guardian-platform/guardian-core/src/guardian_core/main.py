import time
from pathlib import Path

from .command_dispatcher import CommandDispatcher
from .config_manager import ConfigManager
from .guardian_node import GuardianNode
from .health import HealthMonitor
from .recovery_manager import RecoveryManager
from .snapshot_manager import SnapshotManager
from .state_manager import StateManager
from .watchdog import Watchdog


def main():
    state_manager = StateManager()
    watchdog = Watchdog(timeout=15)
    monitor = HealthMonitor()
    config = ConfigManager().load("guardian.yaml")
    snapshots = SnapshotManager(Path(config["snapshot_path"]).expanduser())
    recovery = RecoveryManager(snapshots, state_manager)
    guardian = GuardianNode(state_manager, watchdog, monitor, snapshots, recovery)
    dispatcher = CommandDispatcher(guardian)

    watchdog.start()
    try:
        guardian.initialize()
        print("MISIEK AI Guardian Core A1")

        while True:
            watchdog.heartbeat()
            try:
                command = input("> ").strip()
            except EOFError:
                break

            if command == "exit":
                break

            dispatcher.execute(command)
            time.sleep(0.1)
    finally:
        watchdog.stop()


if __name__ == "__main__":
    main()
