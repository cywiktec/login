"""Safety manager: combines estop / watchdog / geofence status and battery into one level.

Publishes the level (NORMAL, WARNING, SAFE_MODE, EMERGENCY_STOP) on /guardian/safety/level.
Consumers (driver, mission manager) MUST stop motion at SAFE_MODE and above. Releasing a latched
level needs `allow_reset:=true`, healthy inputs, and a call to /guardian/safety_reset (after
/guardian/emergency_reset when an e-stop was active).
"""

from rclpy.node import Node
from std_msgs.msg import Bool, Float32, String
from std_srvs.srv import Trigger

from .common import (SERVICE_SAFETY_RESET, TOPIC_BATTERY, TOPIC_ESTOP_ACTIVE, TOPIC_GEOFENCE_OK,
                     TOPIC_LEVEL, TOPIC_STATE, TOPIC_WATCHDOG_OK, command_qos, run, status_qos)
from .logic import SafetyManagerLogic, require_positive
from .state import from_level


class SafetyManager(Node):
    def __init__(self):
        super().__init__("safety_manager")
        self.declare_parameter("allow_reset", False)
        self.declare_parameter("rate_hz", 10.0)
        self.declare_parameter("input_timeout_s", 1.0)
        self.declare_parameter("battery_timeout_s", 10.0)
        self.declare_parameter("startup_grace_s", 5.0)
        self.declare_parameter("battery_low", 30.0)
        self.declare_parameter("battery_critical", 15.0)
        rate = require_positive(self.get_parameter("rate_hz").value, "rate_hz")
        self._allow_reset = bool(self.get_parameter("allow_reset").value)
        self._logic = SafetyManagerLogic(
            input_timeout=self.get_parameter("input_timeout_s").value,
            battery_timeout=self.get_parameter("battery_timeout_s").value,
            startup_grace=self.get_parameter("startup_grace_s").value,
            battery_low=self.get_parameter("battery_low").value,
            battery_critical=self.get_parameter("battery_critical").value,
        )
        self._last = None
        self._pub = self.create_publisher(String, TOPIC_LEVEL, status_qos())
        self._state_pub = self.create_publisher(String, TOPIC_STATE, status_qos())
        for name, topic in (("estop", TOPIC_ESTOP_ACTIVE), ("watchdog", TOPIC_WATCHDOG_OK),
                            ("geofence", TOPIC_GEOFENCE_OK)):
            self.create_subscription(Bool, topic, self._input_callback(name), status_qos())
        self.create_subscription(Float32, TOPIC_BATTERY, self._on_battery, command_qos())
        self.create_service(Trigger, SERVICE_SAFETY_RESET, self._on_reset)
        self.create_timer(1.0 / rate, self._tick)

    def _input_callback(self, name):
        def callback(msg):
            self._logic.update_input(name, msg.data)
            self._tick()  # react immediately, e.g. to an e-stop
        return callback

    def _on_battery(self, msg):
        self._logic.update_battery(msg.data)

    def _tick(self):
        level = self._logic.evaluate()
        self._pub.publish(String(data=level.name))
        self._state_pub.publish(String(data=from_level(level).name))
        level = level.name
        if level != self._last:
            log = self.get_logger().info if level == "NORMAL" else self.get_logger().error
            log(f"safety level: {self._last} -> {level}")
            self._last = level

    def _on_reset(self, request, response):
        if not self._allow_reset:
            response.success, response.message = False, "reset is disabled (allow_reset=false)"
        else:
            response.success, response.message = self._logic.reset()
        self.get_logger().warning(f"safety reset: {response.success} ({response.message})")
        self._tick()
        return response


def main():
    run(SafetyManager)
