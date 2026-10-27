"""Map driver data onto the guardian-interfaces message shapes (plain dicts).

No rclpy dependency: a ROS 2 node can pass these dicts to the generated message
constructors. Field names mirror guardian-interfaces/ros2_msgs.
"""


def battery_status_msg(battery):
    """BatteryStatus.msg fields; battery is BatteryReader.read() output or None."""
    if battery is None:
        return {"has_battery": False, "percent": 0.0, "plugged": False}
    return {
        "has_battery": True,
        "percent": float(battery["percent"]),
        "plugged": bool(battery["plugged"]),
    }


def health_status_msg(cpu, ram, disk):
    return {"cpu_percent": float(cpu), "ram_percent": float(ram), "disk_percent": float(disk)}
