"""Publishes a heartbeat for one named source at a fixed rate.

In the launch file this represents the safety stack itself ("safety_stack"); it proves the
publish/subscribe path works, NOT that guardian_core or the driver are alive. Those components
must publish their own heartbeat (reuse this node with another `source`, or publish directly).
"""

from rclpy.node import Node
from std_msgs.msg import String

from .common import TOPIC_HEARTBEAT, command_qos, run
from .logic import require_positive


class HeartbeatNode(Node):
    def __init__(self):
        super().__init__("heartbeat_node")
        self.declare_parameter("source", "safety_stack")
        self.declare_parameter("rate_hz", 5.0)
        self._source = str(self.get_parameter("source").value)
        if not self._source:
            raise ValueError("source must not be empty")
        rate = require_positive(self.get_parameter("rate_hz").value, "rate_hz")
        self._pub = self.create_publisher(String, TOPIC_HEARTBEAT, command_qos())
        self.create_timer(1.0 / rate, self._beat)

    def _beat(self):
        self._pub.publish(String(data=self._source))


def main():
    run(HeartbeatNode)
