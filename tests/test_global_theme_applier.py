"""Unit tests for safe, verified Global Theme application, diff preview, Safe Mode simulation, and automated rollback."""

import configparser
import json
from pathlib import Path
import subprocess
from unittest.mock import MagicMock, patch
import pytest

from plasmaforge.core.backup_manager import BackupManager
from plasmaforge.core.global_theme_applier import (
    GlobalThemeApplier,
    GlobalThemeApplyResult,
)
from plasmaforge.core.theme_installer import InstalledThemeInfo, ThemePackageInspector
from plasmaforge.core.transaction import TransactionState


def _setup_theme_fixture(tmp_path: Path, theme_id: str = "org.kde.breezedark.desktop") -> Tuple[Path, Path, InstalledThemeInfo]:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    theme_dir = tmp_path / "laf" / theme_id
    theme_dir.mkdir(parents=True)

    # Initial live kdeglobals
    kdeglobals = config_dir / "kdeglobals"
    kdeglobals.write_text("[KDE]\nLookAndFeelPackage=org.kde.breeze.desktop\n\n[General]\nColorScheme=BreezeLight\n")

    # Initial live plasmarc
    plasmarc = config_dir / "plasmarc"
    plasmarc.write_text("[Theme]\nname=default\n")

    # Theme metadata.json
    (theme_dir / "metadata.json").write_text(json.dumps({
        "KPlugin": {
            "Id": theme_id,
            "Name": "Breeze Dark",
            "Version": "6.0",
            "Description": "Breeze Dark Global Theme",
        }
    }))

    # Theme contents/defaults
    contents_dir = theme_dir / "contents"
    contents_dir.mkdir()
    (contents_dir / "defaults").write_text("""[kdeglobals][General]
ColorScheme=BreezeDark

[kdeglobals][Icons]
Theme=breeze-dark

[plasmarc][Theme]
name=breeze-dark

[kcminputrc][Mouse]
cursorTheme=breeze_cursors
""")

    theme_info = InstalledThemeInfo(
        id=theme_id,
        name="Breeze Dark",
        path=str(theme_dir),
        version="6.0",
        author="KDE Community",
        description="Breeze Dark Global Theme",
        is_user_installed=True,
        components={
            "Color Scheme": "BreezeDark",
            "Icon Theme": "breeze-dark",
            "Plasma Desktop Theme": "breeze-dark",
            "Cursor Theme": "breeze_cursors",
        },
        has_defaults=True,
    )

    return config_dir, theme_dir, theme_info


def test_impact_analysis_and_diff(tmp_path: Path) -> None:
    """Verify impact analysis extracts affected components and diff preview."""
    config_dir, theme_dir, theme_info = _setup_theme_fixture(tmp_path)

    applier = GlobalThemeApplier(
        source_config_dir=config_dir,
        safe_mode=True,
    )

    components, affected_files, warnings = applier.analyze_theme_impact(theme_info)
    assert "Color Scheme" in components
    assert "kdeglobals" in affected_files
    assert "plasmarc" in affected_files
    assert "kcminputrc" in affected_files

    diff = applier.generate_diff_preview(theme_info)
    assert "Breeze Dark" in diff
    assert "org.kde.breezedark.desktop" in diff
    assert "ColorScheme = BreezeDark" in diff or "ColorScheme" in diff


def test_safe_mode_simulation_leaves_files_untouched(tmp_path: Path) -> None:
    """Verify Safe Mode creates verified simulation snapshot without modifying live desktop files."""
    config_dir, theme_dir, theme_info = _setup_theme_fixture(tmp_path)
    backup_mgr = BackupManager(backup_root=tmp_path / "snapshots", source_config_dir=config_dir)

    inspector = MagicMock(spec=ThemePackageInspector)
    inspector.list_installed_themes.return_value = [theme_info]

    applier = GlobalThemeApplier(
        backup_manager=backup_mgr,
        safe_mode=True,
        source_config_dir=config_dir,
        inspector=inspector,
    )

    kdeglobals_before = (config_dir / "kdeglobals").read_text()

    result = applier.apply_theme(theme_info.id)
    assert result.success is True
    assert result.is_dry_run is True
    assert "Safe Mode active" in result.message

    # Ensure live file was not modified
    assert (config_dir / "kdeglobals").read_text() == kdeglobals_before


def test_live_apply_success_and_verification(tmp_path: Path) -> None:
    """Verify live apply creates pre-apply backup, runs tool, and verifies configuration."""
    config_dir, theme_dir, theme_info = _setup_theme_fixture(tmp_path)
    backup_mgr = BackupManager(backup_root=tmp_path / "snapshots", source_config_dir=config_dir)

    inspector = MagicMock(spec=ThemePackageInspector)
    inspector.list_installed_themes.return_value = [theme_info]

    mock_tool = tmp_path / "fake-plasma-apply-lookandfeel"
    mock_tool.write_text("#!/bin/sh\nexit 0\n")
    mock_tool.chmod(0o755)

    applier = GlobalThemeApplier(
        backup_manager=backup_mgr,
        safe_mode=False,
        source_config_dir=config_dir,
        tool_binary=str(mock_tool),
        inspector=inspector,
    )

    def fake_execute(tool_args):
        # Simulate tool updating kdeglobals LookAndFeelPackage
        cfg = configparser.ConfigParser(interpolation=None)
        cfg.read(config_dir / "kdeglobals")
        cfg.set("KDE", "LookAndFeelPackage", theme_info.id)
        with open(config_dir / "kdeglobals", "w") as f:
            cfg.write(f)
        return subprocess.CompletedProcess(args=tool_args, returncode=0, stdout="Success", stderr="")

    with patch.object(applier, "_execute_apply_command", side_effect=fake_execute):
        result = applier.apply_theme(theme_info.id)

    assert result.success is True
    assert result.is_dry_run is False
    assert result.backup_id != ""
    assert "Successfully applied" in result.message

    # Verify live file was updated
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(config_dir / "kdeglobals")
    assert cfg.get("KDE", "LookAndFeelPackage") == theme_info.id


def test_apply_failure_triggers_automatic_rollback(tmp_path: Path) -> None:
    """Verify application failure triggers automatic rollback restoring initial configuration."""
    config_dir, theme_dir, theme_info = _setup_theme_fixture(tmp_path)
    backup_mgr = BackupManager(backup_root=tmp_path / "snapshots", source_config_dir=config_dir)

    inspector = MagicMock(spec=ThemePackageInspector)
    inspector.list_installed_themes.return_value = [theme_info]

    initial_content = (config_dir / "kdeglobals").read_text()

    mock_tool = tmp_path / "fake-plasma-apply-lookandfeel"
    mock_tool.write_text("#!/bin/sh\nexit 0\n")
    mock_tool.chmod(0o755)

    applier = GlobalThemeApplier(
        backup_manager=backup_mgr,
        safe_mode=False,
        source_config_dir=config_dir,
        tool_binary=str(mock_tool),
        inspector=inspector,
    )

    def failing_execute(tool_args):
        # Corrupt file then fail
        (config_dir / "kdeglobals").write_text("CORRUPTED")
        return subprocess.CompletedProcess(args=tool_args, returncode=1, stdout="", stderr="Fatal error applying theme")

    with patch.object(applier, "_execute_apply_command", side_effect=failing_execute):
        result = applier.apply_theme(theme_info.id)

    assert result.success is False
    assert result.rolled_back is True
    assert "Automatic rollback restored previous configuration" in result.message

    # Verify rollback restored the original file perfectly
    assert (config_dir / "kdeglobals").read_text() == initial_content


def test_restore_backup_functionality(tmp_path: Path) -> None:
    """Verify manual snapshot restoration through GlobalThemeApplier."""
    config_dir, theme_dir, theme_info = _setup_theme_fixture(tmp_path)
    backup_mgr = BackupManager(backup_root=tmp_path / "snapshots", source_config_dir=config_dir)

    snap = backup_mgr.create_snapshot("Initial Snapshot")

    # Modify live config
    (config_dir / "kdeglobals").write_text("[KDE]\nLookAndFeelPackage=Modified\n")

    applier = GlobalThemeApplier(
        backup_manager=backup_mgr,
        safe_mode=False,
        source_config_dir=config_dir,
    )

    ok, msg = applier.restore_backup(snap.id)
    assert ok is True
    assert "Successfully restored" in msg

    # Verify restoration
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(config_dir / "kdeglobals")
    assert cfg.get("KDE", "LookAndFeelPackage") == "org.kde.breeze.desktop"
