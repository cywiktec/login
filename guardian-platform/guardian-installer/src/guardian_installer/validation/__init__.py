"""Preflight checks. Each returns a Check; the environment is injected so tests need no root."""

import os
import platform
import shutil
from dataclasses import dataclass

from ..profile import detect_profile

MIN_DISK_GB = 10.0  # untuned placeholders
MIN_RAM_GB = 2.0
SUPPORTED_ARCH = ("x86_64", "aarch64")


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str = ""


@dataclass(frozen=True)
class Environment:
    os_release: str
    machine: str
    disk_free_gb: float
    ram_gb: float
    euid: int


def gather_environment(path="/"):
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            os_release = f.read()
    except OSError:
        os_release = ""
    ram_gb = 0.0
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    ram_gb = int(line.split()[1]) / 1024 / 1024
                    break
    except (OSError, ValueError, IndexError):
        pass
    return Environment(os_release, platform.machine(), shutil.disk_usage(path).free / 1e9, ram_gb,
                       os.geteuid() if hasattr(os, "geteuid") else -1)


def preflight(env: Environment):
    """Fails closed: unknown OS, unknown memory or unreadable data count as failures."""
    profile = detect_profile(env.os_release)
    return [
        Check("os", profile is not None,
              f"Ubuntu {profile.version}" if profile else "unsupported or unknown OS (need Ubuntu 22.04/24.04)"),
        Check("arch", env.machine in SUPPORTED_ARCH, env.machine),
        Check("disk", env.disk_free_gb >= MIN_DISK_GB, f"{env.disk_free_gb:.1f} GB free, need {MIN_DISK_GB}"),
        Check("ram", env.ram_gb >= MIN_RAM_GB, f"{env.ram_gb:.1f} GB, need {MIN_RAM_GB}"),
        Check("root", env.euid == 0, "must run as root to install packages"),
    ]


def all_ok(checks):
    return bool(checks) and all(c.ok for c in checks)
