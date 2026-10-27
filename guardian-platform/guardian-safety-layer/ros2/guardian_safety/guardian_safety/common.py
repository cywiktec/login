"""Topic names, QoS profiles and the node runner shared by all guardian_safety nodes."""

import rclpy
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

TOPIC_HEARTBEAT = "/guardian/heartbeat"                  # std_msgs/String: source name
TOPIC_EMERGENCY_STOP = "/guardian/emergency_stop"        # std_msgs/String: reason; any message triggers
TOPIC_POSITION = "/guardian/position"                    # geometry_msgs/PointStamped (map frame, metres)
TOPIC_BATTERY = "/guardian/battery_percent"              # std_msgs/Float32, 0-100
TOPIC_ESTOP_ACTIVE = "/guardian/safety/estop_active"     # std_msgs/Bool
TOPIC_WATCHDOG_OK = "/guardian/safety/watchdog_ok"       # std_msgs/Bool
TOPIC_GEOFENCE_OK = "/guardian/safety/geofence_ok"       # std_msgs/Bool
TOPIC_LEVEL = "/guardian/safety/level"                   # std_msgs/String: NORMAL|WARNING|SAFE_MODE|EMERGENCY_STOP
TOPIC_STATE = "/guardian/safety/state"                   # std_msgs/String: MONITORING|DEGRADED|FAILSAFE|SAFE_MODE|E_STOP
SERVICE_EMERGENCY_RESET = "/guardian/emergency_reset"    # std_srvs/Trigger
SERVICE_SAFETY_RESET = "/guardian/safety_reset"          # std_srvs/Trigger


def command_qos():
    """Reliable, volatile stream (heartbeats, e-stop requests, sensor input)."""
    return QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10,
                      reliability=ReliabilityPolicy.RELIABLE,
                      durability=DurabilityPolicy.VOLATILE)


def status_qos():
    """Reliable state topics; late joiners receive the last value."""
    return QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1,
                      reliability=ReliabilityPolicy.RELIABLE,
                      durability=DurabilityPolicy.TRANSIENT_LOCAL)


def run(node_class):
    """Spins a node; a constructor error (e.g. bad parameters) exits non-zero."""
    rclpy.init()
    node = None
    try:
        node = node_class()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
