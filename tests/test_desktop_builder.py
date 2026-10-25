"""Focused unit tests for Phase 4 Desktop Builder models, detection, presets, controllers, and transactional safety."""

from pathlib import Path
from unittest.mock import MagicMock
import pytest

from plasmaforge.core.backup_manager import BackupManager
from plasmaforge.core.desktop_layout import (
    DesktopLayout,
    DesktopLayoutApplier,
    PanelConfig,
    detect_desktop_layout,
    get_layout_presets,
)
from plasmaforge.core.transaction import TransactionState
from plasmaforge.controllers.desktop_controller import DesktopController


@pytest.fixture
def mock_desktop_env(tmp_path: Path):
    """Setup isolated config and snapshot directories for testing Desktop Builder."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    appletsrc_path = config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
    appletsrc_content = """[Containments][46]
activityId=c145739b-1b05-4165-8181-a4ab99484302
formfactor=0
plugin=org.kde.plasma.folder

[Containments][46][Applets][67]
plugin=com.github.prayag2.modernclock

[Containments][47]
formfactor=2
location=3
plugin=org.kde.panel
thickness=32
visibility=0

[Containments][47][Applets][48]
plugin=org.kde.plasma.kickoff

[Containments][47][Applets][51]
plugin=org.kde.plasma.digitalclock

[Containments][47][Applets][54]
plugin=org.kde.plasma.systemtray

[Containments][61]
formfactor=2
location=4
plugin=org.kde.panel
thickness=48
visibility=2

[Containments][61][Applets][62]
plugin=org.kde.plasma.icontasks
"""
    appletsrc_path.write_text(appletsrc_content, encoding="utf-8")

    backup_dir = tmp_path / "snapshots"
    bm = BackupManager(backup_root=backup_dir, source_config_dir=config_dir)

    applier = DesktopLayoutApplier(
        backup_manager=bm,
        safe_mode=True,
        source_config_dir=config_dir,
    )

    return {
        "config_dir": config_dir,
        "appletsrc_path": appletsrc_path,
        "appletsrc_content": appletsrc_content,
        "backup_manager": bm,
        "backup_dir": backup_dir,
        "applier": applier,
    }


def test_panel_config_validation():
    """Test validation of panel and dock bounds."""
    # Valid panel
    panel = PanelConfig(position="top", thickness=32, visibility="always_visible", icon_size=40)
    assert len(panel.validate()) == 0

    # Invalid position
    bad_pos = PanelConfig(position="diagonal")
    errors = bad_pos.validate()
    assert any("position" in e for e in errors)

    # Thickness out of bounds
    too_thin = PanelConfig(thickness=10)
    assert any("thickness" in e for e in too_thin.validate())

    too_thick = PanelConfig(thickness=200)
    assert any("thickness" in e for e in too_thick.validate())

    # Invalid visibility
    bad_vis = PanelConfig(visibility="invisible")
    assert any("visibility" in e for e in bad_vis.validate())

    # Invalid icon size
    bad_icon = PanelConfig(icon_size=120)
    assert any("icon" in e.lower() for e in bad_icon.validate())


def test_layout_presets_registry():
    """Verify built-in presets: Classic KDE, Nothing-inspired, and Clean Minimal."""
    presets = get_layout_presets()
    preset_ids = [p.id for p in presets]

    assert "classic_kde" in preset_ids
    assert "nothing_inspired" in preset_ids
    assert "clean_minimal" in preset_ids

    for p in presets:
        assert len(p.validate()) == 0
        assert p.is_preset is True

    # Classic KDE properties
    classic = next(p for p in presets if p.id == "classic_kde")
    assert classic.top_panel.position == "none"
    assert classic.dock.position == "bottom"
    assert classic.show_widgets is False

    # Nothing-inspired properties
    nothing = next(p for p in presets if p.id == "nothing_inspired")
    assert nothing.top_panel.position == "top"
    assert nothing.dock.position == "bottom"
    assert nothing.dock.is_dock is True
    assert nothing.show_widgets is True


def test_detect_desktop_layout(mock_desktop_env):
    """Verify accurate detection of containments, positions, and widgets from real config."""
    appletsrc_path = mock_desktop_env["appletsrc_path"]
    detected = detect_desktop_layout(appletsrc_path)

    assert detected.is_detected is True
    assert detected.top_panel.is_detected is True
    assert detected.top_panel.position == "top"
    assert detected.top_panel.thickness == 32
    assert detected.top_panel.visibility == "always_visible"
    assert "kickoff" in detected.top_panel.applets
    assert "systemtray" in detected.top_panel.applets

    assert detected.dock.is_detected is True
    assert detected.dock.position == "bottom"
    assert detected.dock.thickness == 48
    assert detected.dock.visibility == "dodge_windows"
    assert "icontasks" in detected.dock.applets

    assert detected.show_widgets is True  # Containment 46 has modernclock


def test_draft_isolation_from_live_config(mock_desktop_env):
    """Editing the draft layout must not modify detected layout or disk configuration."""
    appletsrc_path = mock_desktop_env["appletsrc_path"]
    original_content = appletsrc_path.read_text(encoding="utf-8")

    ctrl = DesktopController()
    ctrl._backup_manager = mock_desktop_env["backup_manager"]
    ctrl._applier.source_config_dir = mock_desktop_env["config_dir"]
    ctrl.refresh()

    # Modify draft properties
    ctrl.setPanelPosition("bottom")
    ctrl.setPanelThickness(48)
    ctrl.setDockPosition("top")
    ctrl.setShowWidgets(False)

    assert ctrl.isDraftModified is True
    assert ctrl.panelPosition == "bottom"
    assert ctrl.panelThickness == 48
    assert ctrl.dockPosition == "top"
    assert ctrl.showWidgets is False

    # Detected layout must remain untouched
    assert ctrl.detectedLayout["top_panel"]["position"] == "top"
    assert ctrl.detectedLayout["dock"]["position"] == "bottom"

    # Live file on disk must be completely untouched
    assert appletsrc_path.read_text(encoding="utf-8") == original_content

    # Reset draft
    ctrl.resetDraft()
    assert ctrl.isDraftModified is False
    assert ctrl.panelPosition == "top"
    assert ctrl.dockPosition == "bottom"


def test_preset_loading_into_draft(mock_desktop_env):
    """Loading a preset populates the draft without altering disk state."""
    appletsrc_path = mock_desktop_env["appletsrc_path"]
    original_content = appletsrc_path.read_text(encoding="utf-8")

    ctrl = DesktopController()
    ctrl._backup_manager = mock_desktop_env["backup_manager"]
    ctrl.refresh()

    ctrl.loadPreset("classic_kde")
    assert ctrl.selectedPresetId == "classic_kde"
    assert ctrl.panelPosition == "none"
    assert ctrl.dockPosition == "bottom"
    assert ctrl.showWidgets is False
    assert ctrl.isDraftModified is True

    # Live config untouched
    assert appletsrc_path.read_text(encoding="utf-8") == original_content


def test_safe_mode_prevents_live_writes(mock_desktop_env):
    """Safe Mode generates diff previews and test backup without touching live config."""
    applier = mock_desktop_env["applier"]
    appletsrc_path = mock_desktop_env["appletsrc_path"]
    original_content = appletsrc_path.read_text(encoding="utf-8")

    target = DesktopLayout(
        id="test_safe_apply",
        name="Test Safe Apply",
        description="Testing safe mode",
        top_panel=PanelConfig(position="bottom", thickness=44, visibility="auto_hide"),
        dock=PanelConfig(position="top", thickness=50, visibility="always_visible"),
    )

    diff = applier.generate_diff_preview(target)
    assert "Unified Diff Preview" in diff
    assert "plasma-org.kde.plasma.desktop-appletsrc" in diff

    result = applier.apply_layout(target, force_safe_mode=True)
    assert result.success is True
    assert result.is_dry_run is True
    assert result.state == TransactionState.COMMITTED
    assert "Safe Mode active" in result.message
    assert result.backup_id != ""

    # Live file must remain identical
    assert appletsrc_path.read_text(encoding="utf-8") == original_content


def test_live_mode_apply_and_rollback_on_failure(mock_desktop_env):
    """In Live Mode, failure during write or verification triggers automatic rollback."""
    applier = mock_desktop_env["applier"]
    appletsrc_path = mock_desktop_env["appletsrc_path"]
    original_content = appletsrc_path.read_text(encoding="utf-8")

    target = DesktopLayout(
        id="test_live_fail",
        name="Test Failure",
        description="Testing rollback",
        top_panel=PanelConfig(position="bottom", thickness=40),
        dock=PanelConfig(position="none", thickness=40),
    )

    # Force verification failure
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "plasmaforge.core.desktop_layout.detect_desktop_layout",
            lambda path: DesktopLayout(
                id="fake",
                name="Fake",
                description="Fake",
                top_panel=PanelConfig(position="top", containment_id="47"),
                dock=PanelConfig(position="bottom", containment_id="61"),
            ),
        )

        result = applier.apply_layout(target, force_safe_mode=False)

        assert result.success is False
        assert result.state == TransactionState.ROLLED_BACK
        assert result.rolled_back is True
        assert "Changes were automatically rolled back" in result.message

        # Configuration was rolled back to original
        assert appletsrc_path.read_text(encoding="utf-8") == original_content


def test_live_mode_success_and_restore(mock_desktop_env):
    """In Live Mode, valid apply writes verified keys, and can be restored from backup."""
    applier = mock_desktop_env["applier"]
    appletsrc_path = mock_desktop_env["appletsrc_path"]
    original_content = appletsrc_path.read_text(encoding="utf-8")

    target = DesktopLayout(
        id="test_live_success",
        name="Test Live Success",
        description="Testing success",
        top_panel=PanelConfig(position="top", thickness=42, visibility="auto_hide"),
        dock=PanelConfig(position="bottom", thickness=56, visibility="dodge_windows"),
    )

    result = applier.apply_layout(target, force_safe_mode=False)

    assert result.success is True
    assert result.is_dry_run is False
    assert result.state == TransactionState.COMMITTED
    assert result.backup_id != ""

    # Verify keys were written to file
    new_detected = detect_desktop_layout(appletsrc_path)
    assert new_detected.top_panel.thickness == 42
    assert new_detected.top_panel.visibility == "auto_hide"
    assert new_detected.dock.thickness == 56

    # Test restore
    restore_res = applier.safety_engine.restore_snapshot_transactionally(
        snap_id=result.backup_id,
        file_whitelist=["plasma-org.kde.plasma.desktop-appletsrc"],
        confirmed=True,
        force_safe_mode=False,
    )

    assert restore_res.success is True
    assert appletsrc_path.read_text(encoding="utf-8") == original_content
