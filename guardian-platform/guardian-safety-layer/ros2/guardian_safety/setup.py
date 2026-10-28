from glob import glob

from setuptools import find_packages, setup

package_name = "guardian_safety"

setup(
    name=package_name,
    version="1.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/guardian_safety.launch.py"]),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Jakub C.",
    maintainer_email="owner@misiek-ai.local",
    description="MISIEK AI Guardian safety nodes",
    license="Proprietary",
    entry_points={
        "console_scripts": [
            "emergency_stop_node = guardian_safety.emergency_stop_node:main",
            "watchdog_node = guardian_safety.watchdog_node:main",
            "heartbeat_node = guardian_safety.heartbeat_node:main",
            "geofence_node = guardian_safety.geofence_node:main",
            "safety_manager = guardian_safety.safety_manager:main",
        ],
    },
)
