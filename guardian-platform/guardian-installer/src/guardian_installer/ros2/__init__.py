"""ROS 2 installation steps from the official apt repository."""

from ..steps import Step, Write, run

KEYRING = "/usr/share/keyrings/ros-archive-keyring.gpg"
KEY_URL = "https://raw.githubusercontent.com/ros/rosdistro/master/ros.key"
SOURCES = "/etc/apt/sources.list.d/ros2.list"


def steps(profile, arch="amd64"):
    package = f"ros-{profile.ros_distro}-ros-base"
    line = (f"deb [arch={arch} signed-by={KEYRING}] "
            f"http://packages.ros.org/ros2/ubuntu {profile.codename} main\n")
    return [
        Step("ros2-prereqs", "Install curl and gnupg",
             actions=(run("apt-get", "install", "-y", "curl", "gnupg"),)),
        # The key is fetched over HTTPS but not pinned to a fingerprint.
        Step("ros2-key", "Download the ROS apt signing key",
             actions=(run("curl", "-fsSL", "-o", KEYRING, KEY_URL),),
             undo=(run("rm", "-f", KEYRING),),
             check=run("test", "-s", KEYRING)),
        Step("ros2-source", "Add the ROS 2 apt source",
             actions=(Write(SOURCES, line),), undo=(run("rm", "-f", SOURCES),)),
        Step("ros2-update", "Refresh apt metadata", actions=(run("apt-get", "update"),)),
        Step("ros2-install", f"Install {package}",
             actions=(run("apt-get", "install", "-y", package),),
             undo=(run("apt-get", "remove", "-y", package),),
             check=run("dpkg", "-s", package)),
    ]
