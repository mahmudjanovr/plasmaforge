"""Tests for application configuration."""

import json
from pathlib import Path

from plasmaforge.core.config import AppConfig, get_config, save_config


def test_default_config() -> None:
    config = AppConfig()
    assert config.safe_mode is True
    assert config.dry_run is True
    assert config.theme_mode == "dark"
    assert config.window_width == 1080
    assert config.window_height == 720
    assert "snapshots" in config.backup_dir


def test_safe_mode_strictly_enforced() -> None:
    # Attempt to bypass safe_mode via dictionary
    config = AppConfig.from_dict({"safe_mode": False, "theme_mode": "light"})
    assert config.safe_mode is True
    assert config.theme_mode == "light"


def test_save_and_load_config(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.json"
    custom_cfg = AppConfig(
        theme_mode="system",
        enable_animations=False,
        backup_dir=str(tmp_path / "custom_snaps"),
    )
    save_config(custom_cfg, cfg_file)
    assert cfg_file.is_file()

    loaded = get_config(cfg_file)
    assert loaded.theme_mode == "system"
    assert loaded.enable_animations is False
    assert loaded.backup_dir == str(tmp_path / "custom_snaps")
    assert loaded.safe_mode is True


def test_corrupted_config_fallback(tmp_path: Path) -> None:
    cfg_file = tmp_path / "broken_config.json"
    cfg_file.write_text("{invalid json", encoding="utf-8")

    fallback = get_config(cfg_file)
    assert fallback.safe_mode is True
    assert fallback.theme_mode == "dark"
