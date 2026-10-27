"""Geofence node: publishes geofence_ok from /guardian/position.

`polygon` is a required parameter, a flat list [x1, y1, x2, y2, ...] in map metres (frame_id of
the position is NOT checked). Not set or malformed -> the node refuses to start, which the
safety manager then sees as a missing geofence status (SAFE_MODE). A missing, stale, non-finite
or outside position publishes False.
"""

from geometry_msgs.msg import PointStamped
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import Bool

from .common import TOPIC_GEOFENCE_OK, TOPIC_POSITION, command_qos, run, status_qos
from .logic import GeofenceLogic, parse_polygon, require_positive


class GeofenceNode(Node):
    def __init__(self):
        super().__init__("geofence_node")
        self.declare_parameter("polygon", Parameter.Type.DOUBLE_ARRAY)
        self.declare_parameter("position_timeout_s", 1.0)
        self.declare_parameter("rate_hz", 5.0)
        polygon = parse_polygon(self.get_parameter("polygon").value)
        timeout = require_positive(self.get_parameter("position_timeout_s").value, "position_timeout_s")
        rate = require_positive(self.get_parameter("rate_hz").value, "rate_hz")
        self._logic = GeofenceLogic(polygon, timeout)
        self._last = None
        self._pub = self.create_publisher(Bool, TOPIC_GEOFENCE_OK, status_qos())
        self.create_subscription(PointStamped, TOPIC_POSITION, self._on_position, command_qos())
        self.create_timer(1.0 / rate, self._tick)

    def _on_position(self, msg):
        self._logic.update(msg.point.x, msg.point.y)

    def _tick(self):
        status = self._logic.status()
        self._pub.publish(Bool(data=status == "ok"))
        if status != self._last:
            self._last = status
            log = self.get_logger().info if status == "ok" else self.get_logger().error
            log(f"geofence status: {status}")


def main():
    run(GeofenceNode)
