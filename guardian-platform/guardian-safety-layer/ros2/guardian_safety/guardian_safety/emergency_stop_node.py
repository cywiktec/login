"""Latching emergency stop node.

Any message on /guardian/emergency_stop triggers it. The state is republished at `rate_hz` on
/guardian/safety/estop_active so consumers (and the safety manager) notice if this node dies.
Releasing needs `allow_reset:=true` and a call to /guardian/emergency_reset.
"""

from rclpy.node import Node
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger

from .common import (SERVICE_EMERGENCY_RESET, TOPIC_EMERGENCY_STOP, TOPIC_ESTOP_ACTIVE,
                     command_qos, run, status_qos)
from .logic import EmergencyStopLogic, require_positive


class EmergencyStopNode(Node):
    def __init__(self):
        super().__init__("emergency_stop_node")
        self.declare_parameter("allow_reset", False)
        self.declare_parameter("rate_hz", 5.0)
        rate = require_positive(self.get_parameter("rate_hz").value, "rate_hz")
        self._logic = EmergencyStopLogic(bool(self.get_parameter("allow_reset").value))
        self._pub = self.create_publisher(Bool, TOPIC_ESTOP_ACTIVE, status_qos())
        self.create_subscription(String, TOPIC_EMERGENCY_STOP, self._on_command, command_qos())
        self.create_service(Trigger, SERVICE_EMERGENCY_RESET, self._on_reset)
        self.create_timer(1.0 / rate, self._publish)
        self._publish()

    def _publish(self):
        self._pub.publish(Bool(data=self._logic.active))

    def _on_command(self, msg):
        if self._logic.trigger(msg.data):
            self.get_logger().error(f"EMERGENCY STOP: {self._logic.reason}")
        self._publish()

    def _on_reset(self, request, response):
        try:
            self._logic.reset()
        except PermissionError as exc:
            response.success, response.message = False, str(exc)
            self.get_logger().warning(f"emergency reset refused: {exc}")
        else:
            response.success, response.message = True, "emergency stop released"
            self.get_logger().warning("emergency stop released")
            self._publish()
        return response


def main():
    run(EmergencyStopNode)
