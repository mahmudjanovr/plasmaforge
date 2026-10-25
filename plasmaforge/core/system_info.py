"""Safe, non-destructive system and KDE Plasma 6 environment inspection."""

from __future__ import annotations

import configparser
import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class SystemInfo:
    """Snapshot of host and KDE Plasma 6 environment."""

    plasma_version: str
    qt_version: str
    session_type: str
    desktop_environment: str
    distribution: str
    kernel_version: str
    architecture: str
    active_look_and_feel: str
    active_font: str
    active_fixed_font: str
    tools_available: Dict[str, bool]
    is_plasma_6: bool
    safe_mode_active: bool

    def to_dict(self) -> Dict[str, object]:
        return {
            "plasma_version": self.plasma_version,
            "qt_version": self.qt_version,
            "session_type": self.session_type,
            "desktop_environment": self.desktop_environment,
            "distribution": self.distribution,
            "kernel_version": self.kernel_version,
            "architecture": self.architecture,
            "active_look_and_feel": self.active_look_and_feel,
            "active_font": self.active_font,
            "active_fixed_font": self.active_fixed_font,
            "tools_available": self.tools_available,
            "is_plasma_6": self.is_plasma_6,
            "safe_mode_active": self.safe_mode_active,
        }


def detect_plasma_version() -> str:
    """Safely detect KDE Plasma version using standard command or file inspection."""
    plasmashell_bin = shutil.which("plasmashell")
    if plasmashell_bin:
        try:
            output = subprocess.check_output(
                [plasmashell_bin, "--version"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=2.0,
            ).strip()
            # Typically returns "plasmashell 6.8.1"
            match = re.search(r"(\d+\.\d+(?:\.\d+)?)", output)
            if match:
                return match.group(1)
        except Exception:
            pass

    return "Unknown"


def detect_distribution() -> str:
    """Read distribution name from /etc/os-release safely."""
    os_release = Path("/etc/os-release")
    if os_release.is_file():
        try:
            with open(os_release, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip('"\'')
                    if line.startswith("NAME=") and "distro" not in locals():
                        distro = line.split("=", 1)[1].strip('"\'')
            if "distro" in locals():
                return distro
        except Exception:
            pass
    return "Linux"


def read_kdeglobals_info(kdeglobals_path: Optional[Path] = None) -> tuple[str, str, str]:
    """Extract LookAndFeelPackage, font, and fixed font from kdeglobals without modifying it."""
    path = kdeglobals_path or (Path.home() / ".config" / "kdeglobals")
    look_and_feel = "Breeze Dark (Default)"
    font = "System Default"
    fixed_font = "System Monospace"

    if path.is_file():
        try:
            cfg = configparser.ConfigParser(interpolation=None)
            cfg.optionxform = str  # preserve case
            cfg.read(path, encoding="utf-8")

            if cfg.has_section("KDE"):
                laf = cfg.get("KDE", "LookAndFeelPackage", fallback="")
                if laf:
                    look_and_feel = laf

            if cfg.has_section("General"):
                f_val = cfg.get("General", "font", fallback="")
                if f_val:
                    font = f_val.split(",")[0]
                fix_val = cfg.get("General", "fixed", fallback="")
                if fix_val:
                    fixed_font = fix_val.split(",")[0]
        except Exception:
            pass

    return look_and_feel, font, fixed_font


def get_system_info(kdeglobals_path: Optional[Path] = None) -> SystemInfo:
    """Gather all environment and KDE Plasma 6 details."""
    try:
        from PySide6.QtCore import qVersion
        qt_ver = qVersion()
    except Exception:
        qt_ver = "6.x"

    plasma_ver = detect_plasma_version()
    is_plasma_6 = plasma_ver.startswith("6.") or plasma_ver == "Unknown"

    session_type = os.environ.get("XDG_SESSION_TYPE", "wayland")
    desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "KDE")
    distro = detect_distribution()
    kernel_ver = platform.release()
    arch = platform.machine()

    look_and_feel, font, fixed_font = read_kdeglobals_info(kdeglobals_path)

    tools = {
        "plasmashell": bool(shutil.which("plasmashell")),
        "plasma-apply-colorscheme": bool(shutil.which("plasma-apply-colorscheme")),
        "kwriteconfig6": bool(shutil.which("kwriteconfig6")),
        "kreadconfig6": bool(shutil.which("kreadconfig6")),
        "qdbus6": bool(shutil.which("qdbus6")),
    }

    return SystemInfo(
        plasma_version=plasma_ver,
        qt_version=qt_ver,
        session_type=session_type,
        desktop_environment=desktop_env,
        distribution=distro,
        kernel_version=kernel_ver,
        architecture=arch,
        active_look_and_feel=look_and_feel,
        active_font=font,
        active_fixed_font=fixed_font,
        tools_available=tools,
        is_plasma_6=is_plasma_6,
        safe_mode_active=True,
    )
