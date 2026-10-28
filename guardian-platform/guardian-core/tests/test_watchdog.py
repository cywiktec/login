import time
import unittest
from unittest.mock import patch

from guardian_core.watchdog import Watchdog


class WatchdogTests(unittest.TestCase):
    def test_timeout_is_reported_once_and_thread_stops(self):
        watchdog = Watchdog(timeout=0.05)
        with patch("builtins.print") as print_mock:
            watchdog.start()
            time.sleep(0.2)
            watchdog.stop()

        print_mock.assert_called_once_with("[WATCHDOG] timeout!")
        self.assertIsNone(watchdog._thread)
