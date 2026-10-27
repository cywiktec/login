import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

CONFIG_FILES = ("emergency_stop.yaml", "emergency_reset.yaml", "watchdog.yaml", "heartbeat.yaml",
                "geofence.yaml", "safety_rules.yaml", "safety_manager.yaml")
NODES = ("heartbeat_node", "watchdog_node", "geofence_node", "emergency_stop_node", "safety_manager")


def generate_launch_description():
    config = os.path.join(get_package_share_directory("guardian_safety"), "config")
    base = [os.path.join(config, name) for name in CONFIG_FILES]
    override = LaunchConfiguration("params_file")  # optional extra file, loaded last
    return LaunchDescription([
        DeclareLaunchArgument("params_file", default_value=base[0]),
        *[
            Node(package="guardian_safety", executable=name, name=name,
                 parameters=[*base, override], output="screen",
                 # no respawn for the e-stop node: a restart would lose its latch
                 respawn=name != "emergency_stop_node", respawn_delay=1.0)
            for name in NODES
        ],
    ])
