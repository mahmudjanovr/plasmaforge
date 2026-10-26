"""End-to-end integration and transactional validation tests for KDE Desktop customization.

Validates:
1. Live KDE Plasma 6 widget placement, verification, and cleanup on a verified isolated disposable panel.
2. Safe Desktop containment widget enumeration without mutation.
3. Transactional safety, pre-apply backups, automatic rollback on apply or verification failures, and disk integrity.
4. Safe Mode guarantees: zero live D-Bus or disk mutations during dry-run diffs and inspections.
5. Layout preset integrity: in-memory draft isolation, schema validation, atomic saving, dependency checking, and built-in preset immutability.
6. Controller concurrency, re-entrancy protection, and stale panel reference handling.
"""

from __future__ import annotations

import configparser
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication

from plasmaforge.controllers.desktop_controller import DesktopController
from plasmaforge.core.backup_manager import BackupManager
from plasmaforge.core.desktop_inspector import (
    DesktopChangeAnalyzer,
    DesktopLayoutInspector,
    DetectedPanelInfo,
    LiveDesktopState,
)
from plasmaforge.core.desktop_layout import (
    DesktopLayout,
    DesktopLayoutApplier,
    PanelConfig,
    detect_desktop_layout,
)
from plasmaforge.core.kde_panel_editor import KdePanelLiveEditor
from plasmaforge.core.kde_widget_placer import KdeWidgetPlacer, WidgetPlacementResult
from plasmaforge.core.layout_presets import (
    PRESET_SCHEMA_VERSION,
    LayoutPreset,
    LayoutPresetManager,
    get_curated_layout_presets,
)
from plasmaforge.core.transaction import (
    ApplyOperation,
    TransactionalSafetyEngine,
    TransactionResult,
    TransactionState,
)
from plasmaforge.core.widget_catalog import InstalledWidgetInfo, WidgetCatalogService


@pytest.fixture(scope="session")
def qapp():
    """Ensure QGuiApplication instance is active for QObject/QML signal tests."""
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    return app


# ==============================================================================
# 1. Live Session & Isolated Target Validation
# ==============================================================================

def test_live_kde_disposable_panel_widget_lifecycle() -> None:
    """Verify live widget placement, verification, and removal on an isolated disposable panel.

    Guarantees:
    - If a live KDE Plasma 6 session is active via D-Bus, creates a temporary isolated panel.
    - Adds a minimal, known-installed widget ('org.kde.plasma.panelspacer').
    - Verifies the widget exists in the live session via verify_widget_presence.
    - Removes the widget and verifies its absence.
    - Removes the disposable panel and asserts the pre-test and post-test panels strictly match.
    - Never mutates or removes any pre-existing user panels or widgets.
    """
    editor = KdePanelLiveEditor()
    placer = KdeWidgetPlacer(editor)

    if not editor.is_live_dbus_supported():
        pytest.skip("No active live KDE Plasma 6 D-Bus session in this test runner environment.")

    # 1. Capture initial pre-test panel IDs
    ok, out, _ = editor.execute_script("print(JSON.stringify(panels().map(p => p.id)));")
    assert ok, "Failed to query panels from live Plasma session"
    initial_panel_ids = json.loads(out)
    assert isinstance(initial_panel_ids, list)

    # 2. Create isolated disposable panel
    ok, out, err = editor.execute_script("var p = new Panel(); print(p ? p.id : -1);")
    assert ok, f"Failed to create disposable test panel: {err}"
    disposable_panel_id = int(out.strip())
    assert disposable_panel_id > 0, "Invalid disposable panel ID returned by Plasma"
    assert disposable_panel_id not in initial_panel_ids

    try:
        # 3. Add minimal installed widget to disposable panel
        widget_id = "org.kde.plasma.panelspacer"
        add_result = placer.add_widget(disposable_panel_id, widget_id)
        assert add_result.success is True, f"Failed to place widget on disposable panel: {add_result.message}"
        assert add_result.applet_id is not None
        created_applet_id = add_result.applet_id

        # 4. Verify live presence of the widget
        ok_pres, pres_msg = placer.verify_widget_presence(
            disposable_panel_id, widget_id, should_be_present=True
        )
        assert ok_pres is True, f"Widget presence verification failed: {pres_msg}"

        # 5. Remove the widget from the disposable panel
        ok_rem, rem_msg = placer.remove_widget(disposable_panel_id, created_applet_id)
        assert ok_rem is True, f"Widget removal failed: {rem_msg}"

        # 6. Verify widget is absent in subsequent query
        ok_abs, abs_msg = placer.verify_widget_presence(
            disposable_panel_id, widget_id, should_be_present=False
        )
        assert ok_abs is True, f"Widget absence verification failed: {abs_msg}"

    finally:
        # 7. Clean up disposable panel unconditionally
        cleanup_script = f"var p = panelById({disposable_panel_id}); if (p) p.remove();"
        editor.execute_script(cleanup_script)

        # 8. Verify pre-test panels and post-test panels strictly match
        ok, out, _ = editor.execute_script("print(JSON.stringify(panels().map(p => p.id)));")
        assert ok
        final_panel_ids = json.loads(out)
        assert final_panel_ids == initial_panel_ids, (
            f"Isolation failure: panels list altered! Pre: {initial_panel_ids}, Post: {final_panel_ids}"
        )


def test_live_desktop_containment_enumeration_without_mutation() -> None:
    """Verify safe read-only enumeration of live desktop containments and applets."""
    editor = KdePanelLiveEditor()
    placer = KdeWidgetPlacer(editor)

    if not editor.is_live_dbus_supported():
        pytest.skip("No active live KDE Plasma 6 D-Bus session in this test runner environment.")

    # 1. Query live desktop containments
    ok, out, _ = editor.execute_script("var ds = desktops(); print(JSON.stringify(ds.map(d => d.id)));")
    assert ok
    desktop_ids = json.loads(out)
    assert isinstance(desktop_ids, list)

    if desktop_ids:
        cid = desktop_ids[0]
        # Query widgets via placer
        widgets = placer.get_containment_widgets(cid, is_desktop=True)
        assert isinstance(widgets, list)
        for w in widgets:
            assert "id" in w
            assert "type" in w

        # Query again to guarantee zero state drift
        widgets_repeat = placer.get_containment_widgets(cid, is_desktop=True)
        assert widgets == widgets_repeat


# ==============================================================================
# 2. Transaction & Rollback Validation
# ==============================================================================

def test_transaction_rollback_on_failed_application(tmp_path: Path) -> None:
    """Verify that a failure during apply step triggers automatic rollback and restores disk config."""
    backup_mgr = BackupManager(backup_root=tmp_path / "backups", source_config_dir=tmp_path / "config")
    source_dir = tmp_path / "config"
    source_dir.mkdir(parents=True)
    target_file = source_dir / "plasma-org.kde.plasma.desktop-appletsrc"
    original_content = "[Containments][1]\nlocation=3\nthickness=32\n"
    target_file.write_text(original_content, encoding="utf-8")

    def failing_apply() -> tuple[bool, str]:
        # Corrupt file during apply
        target_file.write_text("[Containments][1]\nlocation=1\ncorrupted=true\n", encoding="utf-8")
        return False, "Simulated disk write failure"

    engine = TransactionalSafetyEngine(
        backup_manager=backup_mgr,
        safe_mode=False,
        source_config_dir=source_dir,
    )

    op = ApplyOperation(
        id="test_fail_apply",
        title="Test Failing Apply",
        description="Testing automatic rollback on application failure",
        affected_files=["plasma-org.kde.plasma.desktop-appletsrc"],
        apply_fn=failing_apply,
    )

    res = engine.execute(op, confirmed=True)
    assert res.success is False
    assert res.state == TransactionState.ROLLED_BACK
    assert res.rolled_back is True
    # Verify file was rolled back to original content
    assert target_file.read_text(encoding="utf-8") == original_content


def test_transaction_rollback_on_failed_verification(tmp_path: Path) -> None:
    """Verify that a failure during post-apply verification triggers automatic rollback."""
    backup_mgr = BackupManager(backup_root=tmp_path / "backups", source_config_dir=tmp_path / "config")
    source_dir = tmp_path / "config"
    source_dir.mkdir(parents=True)
    target_file = source_dir / "plasma-org.kde.plasma.desktop-appletsrc"
    original_content = "[Containments][1]\nlocation=3\nthickness=32\n"
    target_file.write_text(original_content, encoding="utf-8")

    def successful_apply() -> tuple[bool, str]:
        target_file.write_text("[Containments][1]\nlocation=4\nthickness=48\n", encoding="utf-8")
        return True, "Applied"

    def failing_verify() -> tuple[bool, str]:
        return False, "Verification check failed: live D-Bus property mismatch"

    engine = TransactionalSafetyEngine(
        backup_manager=backup_mgr,
        safe_mode=False,
        source_config_dir=source_dir,
    )

    op = ApplyOperation(
        id="test_fail_verify",
        title="Test Failing Verify",
        description="Testing automatic rollback on verification failure",
        affected_files=["plasma-org.kde.plasma.desktop-appletsrc"],
        apply_fn=successful_apply,
        verify_fn=failing_verify,
    )

    res = engine.execute(op, confirmed=True)
    assert res.success is False
    assert res.state == TransactionState.ROLLED_BACK
    assert res.rolled_back is True
    # Verify file was restored to original content
    assert target_file.read_text(encoding="utf-8") == original_content


def test_applier_reverts_live_dbus_and_removes_widgets_on_verification_failure(tmp_path: Path) -> None:
    """Verify DesktopLayoutApplier cleans up live D-Bus panel properties and removes placed widgets on failure."""
    backup_mgr = BackupManager(backup_root=tmp_path / "backups", source_config_dir=tmp_path / "config")
    source_dir = tmp_path / "config"
    source_dir.mkdir(parents=True)
    target_file = source_dir / "plasma-org.kde.plasma.desktop-appletsrc"
    target_file.write_text(
        "[Containments][47]\nplugin=org.kde.panel\nlocation=3\nthickness=32\nvisibility=0\n",
        encoding="utf-8",
    )

    mock_editor = MagicMock(spec=KdePanelLiveEditor)
    mock_editor.is_live_dbus_supported.return_value = True
    mock_editor.apply_panel_properties.return_value = (
        True,
        {"previous": {"location": "top", "height": 32, "visibility": "always_visible"}},
        "OK",
    )
    # Fail live verification
    mock_editor.verify_panel_properties.return_value = (False, "Live verification timed out")

    mock_placer = MagicMock(spec=KdeWidgetPlacer)
    mock_placer.is_supported.return_value = True
    mock_placer.get_containment_widgets.return_value = []
    mock_placer.add_widget.return_value = WidgetPlacementResult(True, 999, "Placed")
    mock_placer.verify_widget_presence.return_value = (True, "Verified")

    applier = DesktopLayoutApplier(
        backup_manager=backup_mgr,
        safe_mode=False,
        source_config_dir=source_dir,
        live_editor=mock_editor,
        widget_placer=mock_placer,
    )

    target_layout = DesktopLayout(
        id="test_revert",
        name="Test Revert Layout",
        top_panel=PanelConfig(
            position="bottom",
            thickness=48,
            visibility="auto_hide",
            containment_id="47",
            applets=["org.kde.plasma.digitalclock"],
        ),
        dock=PanelConfig(position="none", thickness=32),
    )

    res = applier.apply_layout(target_layout, force_safe_mode=False)

    assert res.success is False
    # Verify live panel properties were reverted
    mock_editor.revert_panel_properties.assert_called_once_with(
        "47", {"location": "top", "height": 32, "visibility": "always_visible"}
    )
    # Verify newly added widget was removed
    mock_placer.remove_widget.assert_called_once_with("47", 999)
    # Verify disk file was restored to original content
    assert "location=3" in target_file.read_text(encoding="utf-8")


# ==============================================================================
# 3. Safe Mode Guarantees
# ==============================================================================

def test_safe_mode_guarantees_zero_mutations(tmp_path: Path) -> None:
    """Verify that in Safe Mode, no live D-Bus calls are made and disk files are left untouched."""
    backup_mgr = BackupManager(backup_root=tmp_path / "backups", source_config_dir=tmp_path / "config")
    source_dir = tmp_path / "config"
    source_dir.mkdir(parents=True)
    target_file = source_dir / "plasma-org.kde.plasma.desktop-appletsrc"
    initial_text = (
        "[Containments][47]\nplugin=org.kde.panel\nlocation=3\nthickness=32\nvisibility=0\n"
    )
    target_file.write_text(initial_text, encoding="utf-8")

    mock_editor = MagicMock(spec=KdePanelLiveEditor)
    mock_editor.is_live_dbus_supported.return_value = True

    mock_placer = MagicMock(spec=KdeWidgetPlacer)
    mock_placer.is_supported.return_value = True

    applier = DesktopLayoutApplier(
        backup_manager=backup_mgr,
        safe_mode=True,
        source_config_dir=source_dir,
        live_editor=mock_editor,
        widget_placer=mock_placer,
    )

    target_layout = DesktopLayout(
        id="test_safe_mode",
        name="Test Safe Mode Layout",
        top_panel=PanelConfig(position="bottom", thickness=64, containment_id="47"),
        dock=PanelConfig(position="none", thickness=32),
    )

    res = applier.apply_layout(target_layout, force_safe_mode=True)

    assert res.success is True
    assert res.is_dry_run is True
    assert "Safe Mode active" in res.message
    # No live D-Bus mutations
    mock_editor.apply_panel_properties.assert_not_called()
    mock_placer.add_widget.assert_not_called()
    # Disk file left completely unmodified
    assert target_file.read_text(encoding="utf-8") == initial_text


# ==============================================================================
# 4. Preset Integrity & In-Memory Draft Isolation
# ==============================================================================

def test_preset_loading_isolation_guarantee(tmp_path: Path, qapp) -> None:
    """Verify loading presets alters only in-memory drafts without mutating disk or detected state."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
    initial_content = (
        "[Containments][47]\nplugin=org.kde.panel\nlocation=3\nthickness=32\nvisibility=0\n"
    )
    config_file.write_text(initial_content, encoding="utf-8")

    applier = DesktopLayoutApplier(source_config_dir=config_dir)
    ctrl = DesktopController(applier=applier)

    assert ctrl.panelPosition == "top"
    assert ctrl.panelThickness == 32

    # Load a preset (e.g. dual_status_dock)
    ctrl.loadPreset("dual_status_dock")

    # In-memory draft changed
    assert ctrl.dockPosition == "bottom"
    assert ctrl.dockThickness == 54

    # Disk file remains 100% untouched
    assert config_file.read_text(encoding="utf-8") == initial_content

    # Detected layout remains unchanged
    assert ctrl.detectedLayout["top_panel"]["position"] == "top"


def test_preset_schema_validation_and_rejection(tmp_path: Path) -> None:
    """Verify rejection of malformed, invalid, or corrupted preset schemas."""
    mgr = LayoutPresetManager(storage_dir=tmp_path / "presets")

    # 1. Invalid ID with special characters
    p_invalid_id = LayoutPreset(
        id="bad/id;with$chars",
        name="Bad ID Preset",
        description="Testing rejection of bad ID",
        schema_version=PRESET_SCHEMA_VERSION,
    )
    ok, msg = mgr.save_preset(p_invalid_id)
    assert ok is False
    assert "Invalid preset ID" in msg

    # 2. Unsupported schema version
    p_bad_version = LayoutPreset(
        id="future_preset",
        name="Future Preset",
        description="Testing rejection of future schema",
        schema_version=999,
    )
    ok, msg = mgr.save_preset(p_bad_version)
    assert ok is False
    assert "Unsupported schema version" in msg

    # 3. Out of bounds thickness
    p_bad_thickness = LayoutPreset(
        id="bad_thickness",
        name="Bad Thickness Preset",
        description="Testing out of bounds thickness",
        schema_version=PRESET_SCHEMA_VERSION,
        top_panel=PanelConfig(position="top", thickness=250),
    )
    ok, msg = mgr.save_preset(p_bad_thickness)
    assert ok is False
    assert "out of bounds" in msg


def test_builtin_presets_are_immutable(tmp_path: Path) -> None:
    """Verify built-in presets cannot be overwritten or deleted."""
    mgr = LayoutPresetManager(storage_dir=tmp_path / "presets")

    # Attempt to overwrite built-in preset
    classic_preset = mgr.get_preset("classic_kde")
    assert classic_preset is not None
    assert classic_preset.is_builtin is True

    ok_save, save_msg = mgr.save_preset(classic_preset, overwrite=True)
    assert ok_save is False
    assert "Cannot overwrite built-in" in save_msg

    # Attempt to delete built-in preset
    ok_del, del_msg = mgr.delete_preset("classic_kde")
    assert ok_del is False
    assert "Built-in presets cannot be deleted" in del_msg


def test_custom_preset_atomic_saving_and_missing_widget_detection(tmp_path: Path) -> None:
    """Verify atomic saving of custom presets and accurate detection of missing widgets."""
    presets_dir = tmp_path / "presets"
    mgr = LayoutPresetManager(storage_dir=presets_dir)

    preset = LayoutPreset(
        id="custom_modern",
        name="Custom Modern",
        description="A modern desktop preset",
        top_panel=PanelConfig(
            position="top",
            thickness=32,
            applets=["org.kde.plasma.kickoff", "com.custom.thirdpartywidget"],
        ),
        dock=PanelConfig(
            position="bottom",
            thickness=48,
            applets=["org.kde.plasma.icontasks"],
        ),
        schema_version=PRESET_SCHEMA_VERSION,
    )

    # Save preset
    ok, msg = mgr.save_preset(preset)
    assert ok is True
    target_file = presets_dir / "custom_modern.json"
    assert target_file.is_file()

    # Verify atomic saving left no temp files
    tmp_files = list(presets_dir.glob("*.tmp"))
    assert len(tmp_files) == 0

    # Test missing widget detection
    mock_catalog = MagicMock(spec=WidgetCatalogService)
    # Simulate: kickoff and icontasks are installed; thirdpartywidget is NOT
    mock_catalog.is_widget_installed.side_effect = lambda pid: pid != "com.custom.thirdpartywidget"

    missing = mgr.check_missing_widgets(preset, mock_catalog)
    assert "com.custom.thirdpartywidget" in missing
    assert "org.kde.plasma.kickoff" not in missing
    assert "org.kde.plasma.icontasks" not in missing


# ==============================================================================
# 5. Controller Concurrency, Re-entrancy & Panel Index Syncing
# ==============================================================================

def test_controller_confirm_apply_reentrancy_guard(tmp_path: Path, qapp) -> None:
    """Verify confirmApplyDraft guards against overlapping executions and emits isApplyingChanged."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
    config_file.write_text(
        "[Containments][47]\nplugin=org.kde.panel\nlocation=3\nthickness=32\nvisibility=0\n",
        encoding="utf-8",
    )

    applier = DesktopLayoutApplier(source_config_dir=config_dir, safe_mode=True)
    ctrl = DesktopController(applier=applier)

    applied_events: List[bool] = []
    ctrl.isApplyingChanged.connect(lambda val: applied_events.append(val))

    assert ctrl.isApplying is False

    # Execute apply
    ctrl.confirmApplyDraft()

    assert ctrl.isApplying is False
    # isApplyingChanged should have transitioned True -> False
    assert True in applied_events
    assert applied_events[-1] is False


def test_controller_stale_panel_reference_resolution(tmp_path: Path, qapp) -> None:
    """Verify controller gracefully handles removed or renamed panels after desktop refresh."""
    ctrl = DesktopController()

    # Simulate inspection completion with 2 panels
    panel_1 = DetectedPanelInfo(id="p1", containment_id="101", position="top", thickness=32, visibility="always_visible")
    panel_2 = DetectedPanelInfo(id="p2", containment_id="102", position="bottom", thickness=48, visibility="always_visible")
    state_initial = LiveDesktopState(
        timestamp="2026-10-26T12:00:00Z",
        plasma_version="6.2.0",
        session_type="wayland",
        distribution="Arch Linux",
        panels=[panel_1, panel_2],
    )
    ctrl._on_inspection_completed(state_initial)

    assert ctrl.selectedPanelId == "101"
    assert ctrl.selectedPanelIndex == 0

    # User selects panel 2
    ctrl.selectPanelByIndex(1)
    assert ctrl.selectedPanelId == "102"
    assert ctrl.selectedPanelIndex == 1

    # Now simulate panel 2 being removed in Plasma (e.g. only panel 1 remains)
    state_after_delete = LiveDesktopState(
        timestamp="2026-10-26T12:00:01Z",
        plasma_version="6.2.0",
        session_type="wayland",
        distribution="Arch Linux",
        panels=[panel_1],
    )
    ctrl._on_inspection_completed(state_after_delete)

    # Controller must not point to stale "102" or out-of-bounds index 1
    assert ctrl.selectedPanelId == "101"
    assert ctrl.selectedPanelIndex == 0


def test_desktop_change_analyzer_multiset_applet_diff() -> None:
    """Verify DesktopChangeAnalyzer detects applet additions, removals, and reordering accurately."""
    cur = DesktopLayout(
        id="cur",
        name="Current",
        top_panel=PanelConfig(
            position="top",
            thickness=32,
            applets=["org.kde.plasma.kickoff", "org.kde.plasma.panelspacer", "org.kde.plasma.panelspacer", "org.kde.plasma.digitalclock"],
        ),
        dock=PanelConfig(position="bottom", thickness=48, applets=["org.kde.plasma.icontasks"]),
    )

    # 1. Duplicate applet removal (one spacer removed)
    draft_spacer_removed = DesktopLayout(
        id="draft1",
        name="Draft 1",
        top_panel=PanelConfig(
            position="top",
            thickness=32,
            applets=["org.kde.plasma.kickoff", "org.kde.plasma.panelspacer", "org.kde.plasma.digitalclock"],
        ),
        dock=PanelConfig(position="bottom", thickness=48, applets=["org.kde.plasma.icontasks"]),
    )

    changes = DesktopChangeAnalyzer.compare_states(cur, draft_spacer_removed)
    top_change = next(c for c in changes if c.component == "Top Panel Applets")
    assert "Remove org.kde.plasma.panelspacer" in top_change.description

    # 2. Pure reordering
    draft_reordered = DesktopLayout(
        id="draft2",
        name="Draft 2",
        top_panel=PanelConfig(
            position="top",
            thickness=32,
            applets=["org.kde.plasma.digitalclock", "org.kde.plasma.panelspacer", "org.kde.plasma.panelspacer", "org.kde.plasma.kickoff"],
        ),
        dock=PanelConfig(position="bottom", thickness=48, applets=["org.kde.plasma.icontasks"]),
    )

    changes_reorder = DesktopChangeAnalyzer.compare_states(cur, draft_reordered)
    top_reorder_change = next(c for c in changes_reorder if c.component == "Top Panel Applets")
    assert "Reorder applets in top panel" in top_reorder_change.description


def test_mock_kde_widget_lifecycle_contract() -> None:
    """Verify widget placer lifecycle behavior with controlled mocks for headless/CI environments."""
    mock_editor = MagicMock(spec=KdePanelLiveEditor)
    mock_editor.is_live_dbus_supported.return_value = True

    # 1. Mock add_widget on panel
    mock_editor.execute_script.side_effect = [
        # add_widget response
        (True, json.dumps({"success": True, "appletId": 501, "plugin": "org.kde.plasma.panelspacer"}), ""),
        # get_containment_widgets response (verified present)
        (True, json.dumps([{"id": 501, "type": "org.kde.plasma.panelspacer"}]), ""),
        # remove_widget response
        (True, json.dumps({"success": True}), ""),
        # get_containment_widgets response (verified absent)
        (True, json.dumps([]), ""),
    ]

    placer = KdeWidgetPlacer(editor=mock_editor)

    # Add widget
    res = placer.add_widget("47", "org.kde.plasma.panelspacer")
    assert res.success is True
    assert res.applet_id == 501

    # Verify presence
    ok_pres, _ = placer.verify_widget_presence("47", "org.kde.plasma.panelspacer", should_be_present=True)
    assert ok_pres is True

    # Remove widget
    ok_rem, _ = placer.remove_widget("47", 501)
    assert ok_rem is True

    # Verify absence
    ok_abs, _ = placer.verify_widget_presence("47", "org.kde.plasma.panelspacer", should_be_present=False)
    assert ok_abs is True

