"""Tests for KDE Plasma 6 Live Panel Editor, Transactional Layout Applier, and Desktop Controller editing."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from plasmaforge.core.backup_manager import BackupManager
from plasmaforge.core.desktop_layout import (
    DesktopLayout,
    DesktopLayoutApplier,
    PanelConfig,
    detect_desktop_layout,
)
from plasmaforge.core.kde_panel_editor import (
    KdePanelLiveEditor,
    PanelHidingMode,
    VISIBILITY_NAME_TO_SCRIPT,
)
from plasmaforge.core.transaction import TransactionState
from plasmaforge.controllers.desktop_controller import DesktopController
from plasmaforge.core.desktop_inspector import (
    DetectedPanelInfo,
    LiveDesktopState,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_appletsrc(tmp_path: Path):
    """Isolated config environment for panel editor and applier tests."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    appletsrc_file = config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
    content = """[Containments][47]
formfactor=2
location=3
plugin=org.kde.panel
thickness=32
visibility=0

[Containments][47][Applets][48]
plugin=org.kde.plasma.kickoff

[Containments][61]
formfactor=2
location=4
plugin=org.kde.panel
thickness=48
visibility=2

[Containments][61][Applets][62]
plugin=org.kde.plasma.icontasks
"""
    appletsrc_file.write_text(content, encoding="utf-8")
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir(parents=True)
    bm = BackupManager(backup_root=backup_dir, source_config_dir=config_dir)

    return {
        "config_dir": config_dir,
        "appletsrc_file": appletsrc_file,
        "backup_manager": bm,
        "content": content,
    }


# ============================================================================
# 1. KdePanelLiveEditor Unit Tests
# ============================================================================

def test_is_live_dbus_supported_missing_qdbus():
    """Returns False when qdbus tool cannot be found."""
    editor = KdePanelLiveEditor(qdbus_bin="")
    assert editor.is_live_dbus_supported() is False


def test_is_live_dbus_supported_plasmashell_inactive():
    """Returns False when plasmashell D-Bus service is not responding."""
    editor = KdePanelLiveEditor(qdbus_bin="/usr/bin/qdbus6")
    with patch.object(editor, "execute_script", return_value=(False, "", "Service unknown")):
        assert editor.is_live_dbus_supported() is False


def test_is_live_dbus_supported_active():
    """Returns True when qdbus responds with active PlasmaShell methods."""
    editor = KdePanelLiveEditor(qdbus_bin="/usr/bin/qdbus6")
    with patch.object(editor, "execute_script", return_value=(True, "ping\n", "")):
        assert editor.is_live_dbus_supported() is True


def test_get_live_panel_parsing():
    """Parses JSON state of running panel returned by evaluateScript."""
    editor = KdePanelLiveEditor(qdbus_bin="/usr/bin/qdbus6")
    sample_json = json.dumps({
        "found": True,
        "id": 47,
        "location": "top",
        "height": 28,
        "hiding": "none",
        "floating": True,
    })

    with patch.object(editor, "execute_script", return_value=(True, sample_json, "")):
        panel = editor.get_live_panel("47")
        assert panel is not None
        assert panel["id"] == "47"
        assert panel["location"] == "top"
        assert panel["height"] == 28
        assert panel["hiding_raw"] == "none"
        assert panel["visibility"] == "always_visible"


def test_get_live_panel_not_found():
    """Returns None when panel ID does not exist or evaluateScript errors."""
    editor = KdePanelLiveEditor(qdbus_bin="/usr/bin/qdbus6")
    with patch.object(editor, "execute_script", return_value=(False, "", "Panel not found")):
        panel = editor.get_live_panel("999")
        assert panel is None


def test_apply_panel_properties_validation():
    """Validates parameters before executing any subprocess."""
    editor = KdePanelLiveEditor(qdbus_bin="/usr/bin/qdbus6")

    # Out of bounds thickness (< 16 or > 128)
    ok, audit, msg = editor.apply_panel_properties(47, location="top", height=10)
    assert ok is False
    assert "bounds" in msg

    ok, audit, msg = editor.apply_panel_properties(47, location="top", height=200)
    assert ok is False
    assert "bounds" in msg

    # Invalid location
    ok, audit, msg = editor.apply_panel_properties(47, location="diagonal", height=32)
    assert ok is False
    assert "location" in msg or "position" in msg

    # Invalid visibility
    ok, audit, msg = editor.apply_panel_properties(47, location="top", height=32, visibility="transparent")
    assert ok is False
    assert "visibility" in msg


def test_apply_panel_properties_execution_success():
    """Applies valid properties, returning previous and updated audit states."""
    editor = KdePanelLiveEditor(qdbus_bin="/usr/bin/qdbus6")
    sample_audit = json.dumps({
        "success": True,
        "previous": {"id": "47", "location": "top", "height": 28, "hiding": "none"},
        "current": {"id": "47", "location": "bottom", "height": 44, "hiding": "autohide"},
    })

    with patch.object(editor, "execute_script", return_value=(True, sample_audit, "")):
        ok, audit, msg = editor.apply_panel_properties(
            containment_id="47",
            location="bottom",
            height=44,
            visibility="auto_hide",
        )
        assert ok is True
        assert audit["previous"]["location"] == "top"
        assert audit["current"]["location"] == "bottom"
        assert audit["current"]["height"] == 44
        assert audit["current"]["visibility"] == "auto_hide"


def test_apply_panel_properties_subprocess_timeout():
    """Handles subprocess timeout error without crashing."""
    editor = KdePanelLiveEditor(qdbus_bin="/usr/bin/qdbus6")
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["qdbus6"], timeout=2.0)):
        ok, out, err = editor.execute_script("print(1);")
        assert ok is False
        assert "timed out" in err


def test_revert_panel_properties():
    """Reverts panel state using previous state audit dictionary."""
    editor = KdePanelLiveEditor(qdbus_bin="/usr/bin/qdbus6")
    prev = {"location": "top", "height": 28, "hiding": "none"}

    sample_revert = json.dumps({
        "success": True,
        "previous": {"id": "47", "location": "bottom", "height": 44, "hiding": "autohide"},
        "current": {"id": "47", "location": "top", "height": 28, "hiding": "none"},
    })

    with patch.object(editor, "execute_script", return_value=(True, sample_revert, "")):
        ok, msg = editor.revert_panel_properties("47", prev)
        assert ok is True


def test_verify_panel_properties():
    """Verifies live panel properties against expected values."""
    editor = KdePanelLiveEditor(qdbus_bin="/usr/bin/qdbus6")

    # Matches
    live_state = {"id": "47", "location": "top", "height": 32, "hiding_raw": "none", "visibility": "always_visible"}
    with patch.object(editor, "get_live_panel", return_value=live_state):
        ok, msg = editor.verify_panel_properties(
            containment_id="47",
            expected_location="top",
            expected_height=32,
            expected_visibility="always_visible",
        )
        assert ok is True

    # Height mismatch
    with patch.object(editor, "get_live_panel", return_value=live_state):
        ok, msg = editor.verify_panel_properties(
            containment_id="47",
            expected_location="top",
            expected_height=48,
            expected_visibility="always_visible",
        )
        assert ok is False
        assert "height" in msg.lower() or "Height" in msg


# ============================================================================
# 2. DesktopLayoutApplier Live Integration Tests
# ============================================================================

def test_applier_safe_mode_skips_live_dbus(mock_appletsrc):
    """In Safe Mode, live D-Bus methods are never invoked."""
    mock_editor = MagicMock(spec=KdePanelLiveEditor)
    mock_editor.is_live_dbus_supported.return_value = True

    applier = DesktopLayoutApplier(
        backup_manager=mock_appletsrc["backup_manager"],
        safe_mode=True,
        source_config_dir=mock_appletsrc["config_dir"],
        live_editor=mock_editor,
    )

    target = DesktopLayout(
        id="test_safe_layout",
        name="Test Safe",
        description="",
        top_panel=PanelConfig(position="top", thickness=36, containment_id="47"),
        dock=PanelConfig(position="bottom", thickness=50, containment_id="61"),
    )

    res = applier.apply_layout(target, force_safe_mode=True)
    assert res.success is True
    assert res.is_dry_run is True
    # Live editor apply must NOT have been called in dry run / safe mode
    mock_editor.apply_panel_properties.assert_not_called()


def test_applier_live_mode_success(mock_appletsrc):
    """In Live Mode with live D-Bus support, applies to disk and D-Bus and verifies both."""
    mock_editor = MagicMock(spec=KdePanelLiveEditor)
    mock_editor.is_live_dbus_supported.return_value = True
    mock_editor.apply_panel_properties.return_value = (
        True,
        {"previous": {"location": "top", "height": 32, "hiding": "none"}},
        "OK",
    )
    mock_editor.verify_panel_properties.return_value = (True, "Verified")

    applier = DesktopLayoutApplier(
        backup_manager=mock_appletsrc["backup_manager"],
        safe_mode=False,
        source_config_dir=mock_appletsrc["config_dir"],
        live_editor=mock_editor,
    )

    target = DesktopLayout(
        id="test_live_apply",
        name="Live Apply",
        description="",
        top_panel=PanelConfig(position="top", thickness=40, containment_id="47"),
        dock=PanelConfig(position="bottom", thickness=54, containment_id="61"),
    )

    res = applier.apply_layout(target, force_safe_mode=False)
    assert res.success is True
    assert res.is_dry_run is False
    assert res.state == TransactionState.COMMITTED

    # Verified live D-Bus apply was called
    mock_editor.apply_panel_properties.assert_called()
    mock_editor.verify_panel_properties.assert_called()

    # Verified disk config was updated
    detected = detect_desktop_layout(mock_appletsrc["appletsrc_file"])
    assert detected.top_panel.position == "top"
    assert detected.top_panel.thickness == 40
    assert detected.dock.thickness == 54


def test_applier_live_verification_failure_triggers_rollback(mock_appletsrc):
    """Live verification failure rolls back disk changes and reverts live D-Bus properties."""
    mock_editor = MagicMock(spec=KdePanelLiveEditor)
    mock_editor.is_live_dbus_supported.return_value = True
    mock_editor.apply_panel_properties.return_value = (
        True,
        {"previous": {"location": "top", "height": 32, "hiding": "none"}},
        "OK",
    )
    # Simulate live verification failure
    mock_editor.verify_panel_properties.return_value = (False, "Height mismatch on live panel")

    applier = DesktopLayoutApplier(
        backup_manager=mock_appletsrc["backup_manager"],
        safe_mode=False,
        source_config_dir=mock_appletsrc["config_dir"],
        live_editor=mock_editor,
    )

    target = DesktopLayout(
        id="test_live_fail",
        name="Live Fail",
        description="",
        top_panel=PanelConfig(position="bottom", thickness=40, containment_id="47"),
        dock=PanelConfig(position="none", thickness=48, containment_id="61"),
    )

    res = applier.apply_layout(target, force_safe_mode=False)
    assert res.success is False
    assert res.state == TransactionState.ROLLED_BACK
    assert res.rolled_back is True

    # Live D-Bus revert must have been called
    mock_editor.revert_panel_properties.assert_called_with(
        "47",
        {"location": "top", "height": 32, "hiding": "none"},
    )

    # Disk config must have rolled back to original
    assert mock_appletsrc["appletsrc_file"].read_text(encoding="utf-8") == mock_appletsrc["content"]


# ============================================================================
# 3. DesktopController Panel Selection and Workbench Tests
# ============================================================================

def test_controller_panel_selection_and_editing(mock_appletsrc):
    """Tests multi-panel selection, property modification, and draft isolation in DesktopController."""
    mock_editor = MagicMock(spec=KdePanelLiveEditor)
    mock_editor.is_live_dbus_supported.return_value = True

    applier = DesktopLayoutApplier(
        backup_manager=mock_appletsrc["backup_manager"],
        safe_mode=True,
        source_config_dir=mock_appletsrc["config_dir"],
        live_editor=mock_editor,
    )

    ctrl = DesktopController(applier=applier)

    # Supply mock detected panels to live state
    sample_panels = [
        DetectedPanelInfo(id="p_47", containment_id="47", position="top", thickness=32, visibility="always_visible"),
        DetectedPanelInfo(id="p_61", containment_id="61", position="bottom", thickness=48, visibility="dodge_windows", is_dock=True),
    ]
    ctrl._live_state.panels = sample_panels
    ctrl.selectPanel("47")

    assert ctrl.selectedPanelId == "47"
    assert ctrl.selectedPanelPosition == "top"
    assert ctrl.selectedPanelThickness == 32
    assert ctrl.selectedPanelVisibility == "always_visible"
    assert ctrl.selectedPanelHasChanges is False
    assert ctrl.isLiveEditingSupported is True
    assert ctrl.selectedPanelIsLiveSupported is True

    # Edit selected panel properties
    ctrl.setSelectedPanelPosition("bottom")
    ctrl.setSelectedPanelThickness(42)
    ctrl.setSelectedPanelVisibility("auto_hide")

    assert ctrl.selectedPanelPosition == "bottom"
    assert ctrl.selectedPanelThickness == 42
    assert ctrl.selectedPanelVisibility == "auto_hide"
    assert ctrl.selectedPanelHasChanges is True
    assert ctrl.isDraftModified is True

    # Disk must remain unmutated (draft isolation)
    assert mock_appletsrc["appletsrc_file"].read_text(encoding="utf-8") == mock_appletsrc["content"]

    # Select second panel
    ctrl.selectPanel("61")
    assert ctrl.selectedPanelId == "61"
    assert ctrl.selectedPanelPosition == "bottom"
    assert ctrl.selectedPanelThickness == 48

    # Reset draft discards modifications
    ctrl.resetDraft()
    assert ctrl.isDraftModified is False
    ctrl.selectPanel("47")
    assert ctrl.selectedPanelPosition == "top"
    assert ctrl.selectedPanelThickness == 32
    assert ctrl.selectedPanelHasChanges is False


def test_controller_apply_and_restore_workflow(mock_appletsrc):
    """Tests the full apply request -> confirm -> restore workflow in DesktopController."""
    mock_editor = MagicMock(spec=KdePanelLiveEditor)
    mock_editor.is_live_dbus_supported.return_value = False  # config only

    applier = DesktopLayoutApplier(
        backup_manager=mock_appletsrc["backup_manager"],
        safe_mode=False,
        source_config_dir=mock_appletsrc["config_dir"],
        live_editor=mock_editor,
    )

    ctrl = DesktopController(applier=applier)
    ctrl.selectPanel("47")
    ctrl.setSelectedPanelThickness(52)

    # 1. Request apply (opens dialog)
    ctrl.requestApplyDraft()
    assert ctrl.showConfirmDialog is True
    assert "Unified Diff" in ctrl.currentDiffPreview

    # 2. Cancel apply
    ctrl.cancelApply()
    assert ctrl.showConfirmDialog is False

    # 3. Confirm apply (mocking safe_mode=False)
    apply_finished_results = []
    ctrl.applyFinished.connect(lambda s, m, d: apply_finished_results.append((s, m, d)))

    with patch("plasmaforge.controllers.desktop_controller.get_config") as mock_get_cfg:
        mock_get_cfg.return_value = MagicMock(safe_mode=False)
        ctrl.requestApplyDraft()
        ctrl.confirmApplyDraft()

    assert len(apply_finished_results) == 1
    assert apply_finished_results[0][0] is True  # success
    assert ctrl.canRestorePrevious is True
    assert ctrl.lastBackupId != ""

    # Check file was modified
    detected = detect_desktop_layout(mock_appletsrc["appletsrc_file"])
    assert detected.top_panel.thickness == 52

    # 4. Restore previous layout
    restore_results = []
    ctrl.restoreFinished.connect(lambda s, m: restore_results.append((s, m)))

    with patch("plasmaforge.controllers.desktop_controller.get_config") as mock_get_cfg:
        mock_get_cfg.return_value = MagicMock(safe_mode=False)
        ctrl.restorePreviousLayout()

    assert len(restore_results) == 1
    assert restore_results[0][0] is True  # success
    assert ctrl.canRestorePrevious is False

    # Check file was restored to original
    restored = detect_desktop_layout(mock_appletsrc["appletsrc_file"])
    assert restored.top_panel.thickness == 32
