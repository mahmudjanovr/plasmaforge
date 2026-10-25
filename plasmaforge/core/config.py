"""Application configuration management for PlasmaForge."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict


def get_default_config_dir() -> Path:
    """Return XDG-compliant configuration directory."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "plasmaforge"
    return Path.home() / ".config" / "plasmaforge"


def get_default_backup_dir() -> Path:
    """Return XDG-compliant snapshot storage directory."""
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        return Path(xdg_data) / "plasmaforge" / "snapshots"
    return Path.home() / ".local" / "share" / "plasmaforge" / "snapshots"


@dataclass
class AppConfig:
    """Runtime configuration for PlasmaForge."""

    safe_mode: bool = True
    dry_run: bool = True
    backup_dir: str = ""
    theme_mode: str = "dark"
    enable_animations: bool = True
    window_width: int = 1080
    window_height: int = 720
    auto_backup_on_preview: bool = True
    last_backup_id: str = ""
    previous_scheme_id: str = ""

    def __post_init__(self) -> None:
        if not self.backup_dir:
            self.backup_dir = str(get_default_backup_dir())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AppConfig:
        allowed = {
            "safe_mode",
            "dry_run",
            "backup_dir",
            "theme_mode",
            "enable_animations",
            "window_width",
            "window_height",
            "auto_backup_on_preview",
            "last_backup_id",
            "previous_scheme_id",
        }
        filtered = {k: v for k, v in data.items() if k in allowed}
        return cls(**filtered)


_GLOBAL_CONFIG: AppConfig | None = None


def get_config(config_file: Path | None = None) -> AppConfig:
    """Load configuration from disk or return cached/default."""
    global _GLOBAL_CONFIG
    if config_file is None and _GLOBAL_CONFIG is not None:
        return _GLOBAL_CONFIG

    target_file = config_file or (get_default_config_dir() / "config.json")
    if target_file.is_file():
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = AppConfig.from_dict(data)
                if config_file is None:
                    _GLOBAL_CONFIG = config
                return config
        except Exception:
            # Fallback to defaults on corrupted file
            pass

    config = AppConfig()
    if config_file is None:
        _GLOBAL_CONFIG = config
    return config


def save_config(config: AppConfig, config_file: Path | None = None) -> Path:
    """Persist configuration to disk."""
    target_file = config_file or (get_default_config_dir() / "config.json")
    target_file.parent.mkdir(parents=True, exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2)
    return target_file
