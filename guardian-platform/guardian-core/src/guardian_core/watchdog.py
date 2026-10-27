import threading
import time


class Watchdog:
    def __init__(self, timeout=15):
        if timeout <= 0:
            raise ValueError("timeout must be positive")

        self.timeout = timeout
        self._last_heartbeat = time.monotonic()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return

        self._last_heartbeat = time.monotonic()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def heartbeat(self):
        with self._lock:
            self._last_heartbeat = time.monotonic()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def _monitor(self):
        while not self._stop_event.wait(min(self.timeout / 4, 1)):
            with self._lock:
                elapsed = time.monotonic() - self._last_heartbeat

            if elapsed > self.timeout:
                print("[WATCHDOG] timeout!")
                return
