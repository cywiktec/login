"""Heartbeat supervisor: publishes watchdog_ok = False when a required source goes silent.

Sources publish their name as std_msgs/String on /guardian/heartbeat. A required source that
never reports expires after `timeout_s` from node start.
"""

from rclpy.node import Node
from std_msgs.msg import Bool, String

from .common import TOPIC_HEARTBEAT, TOPIC_WATCHDOG_OK, command_qos, run, status_qos
from .logic import WatchdogLogic, require_positive


class WatchdogNode(Node):
    def __init__(self):
        super().__init__("watchdog_node")
        self.declare_parameter("required_sources", ["safety_stack"])
        self.declare_parameter("timeout_s", 1.0)
        self.declare_parameter("rate_hz", 5.0)
        timeout = require_positive(self.get_parameter("timeout_s").value, "timeout_s")
        rate = require_positive(self.get_parameter("rate_hz").value, "rate_hz")
        self._logic = WatchdogLogic(list(self.get_parameter("required_sources").value), timeout)
        self._last = None
        self._pub = self.create_publisher(Bool, TOPIC_WATCHDOG_OK, status_qos())
        self.create_subscription(String, TOPIC_HEARTBEAT, self._on_heartbeat, command_qos())
        self.create_timer(1.0 / rate, self._tick)

    def _on_heartbeat(self, msg):
        self._logic.beat(msg.data)

    def _tick(self):
        expired = self._logic.expired()
        ok = not expired
        self._pub.publish(Bool(data=ok))
        if ok != self._last:
            self._last = ok
            if ok:
                self.get_logger().info("all required heartbeats present")
            else:
                self.get_logger().error(f"heartbeat missing: {expired}")


def main():
    run(WatchdogNode)
