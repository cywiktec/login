"""Docker installation steps (Ubuntu's own `docker.io` package, no third-party repository)."""

from ..steps import Step, run


def steps(profile):
    return [
        Step("docker-install", "Install Docker from the Ubuntu archive",
             actions=(run("apt-get", "install", "-y", "docker.io"),),
             undo=(run("apt-get", "remove", "-y", "docker.io"),),
             check=run("docker", "--version")),
        Step("docker-enable", "Enable and start the Docker service",
             actions=(run("systemctl", "enable", "--now", "docker"),),
             undo=(run("systemctl", "disable", "--now", "docker"),),
             check=run("systemctl", "is-active", "--quiet", "docker")),
    ]
