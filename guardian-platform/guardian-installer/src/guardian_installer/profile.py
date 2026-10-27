"""OS profiles and detection."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    version: str
    codename: str
    ros_distro: str
    python: str


def parse_os_release(text):
    out = {}
    for line in text.splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, _, value = line.partition("=")
            out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def detect_profile(os_release_text):
    """Returns the matching Profile, or None for anything that is not a supported Ubuntu."""
    from .ubuntu22 import PROFILE as U22
    from .ubuntu24 import PROFILE as U24

    info = parse_os_release(os_release_text)
    if info.get("ID") != "ubuntu":
        return None
    return {U22.version: U22, U24.version: U24}.get(info.get("VERSION_ID"))
