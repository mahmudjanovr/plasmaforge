"""Tests for application controllers."""

from pathlib import Path
from PySide6.QtGui import QGuiApplication
import pytest

from plasmaforge.core.backup_manager import BackupManager
from plasmaforge.controllers import (
    AppController,
    BackupController,
    PresetController,
    SettingsController,
    SystemController,
    ThemeController,
    DesktopController,
)


@pytest.fixture(scope="session")
def qapp() -> QGuiApplication:
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(["test", "-platform", "offscreen"])
    return app


def test_app_controller_navigation(qapp: QGuiApplication) -> None:
    ctrl = AppController()
    assert ctrl.activeSection == "Overview"
    assert ctrl.safeMode is True

    visited = []
    ctrl.activeSectionChanged.connect(lambda s: visited.append(s))

    ctrl.navigateTo("Theme Studio")
    assert ctrl.activeSection == "Theme Studio"

    ctrl.navigateTo("Settings")
    assert ctrl.activeSection == "Settings"

    # Invalid navigation should be ignored
    ctrl.navigateTo("NonExistentView")
    assert ctrl.activeSection == "Settings"

    assert visited == ["Theme Studio", "Settings"]


def test_preset_controller(qapp: QGuiApplication) -> None:
    ctrl = PresetController()
    assert len(ctrl.presets) >= 4
    assert ctrl.selectedIndex == 0
    assert "Obsidian" in ctrl.selectedPreset["title"]
    assert "Dry-Run" in ctrl.previewText

    ctrl.selectPreset(1)
    assert ctrl.selectedIndex == 1
    assert "Nordic" in ctrl.selectedPreset["title"]


def test_settings_controller(qapp: QGuiApplication) -> None:
    ctrl = SettingsController()
    assert ctrl.safeMode is True

    ctrl.setThemeMode("light")
    assert ctrl.themeMode == "light"
    ctrl.setThemeMode("dark")
    assert ctrl.themeMode == "dark"

    initial_anim = ctrl.enableAnimations
    ctrl.setEnableAnimations(not initial_anim)
    assert ctrl.enableAnimations != initial_anim
    ctrl.setEnableAnimations(initial_anim)


def test_theme_controller_workflow(qapp: QGuiApplication) -> None:
    ctrl = ThemeController()
    assert len(ctrl.colorSchemes) >= 1
    assert ctrl.activeSchemeId != ""

    # Test scheme selection: choose a non-active scheme if available
    target_idx = 0
    for idx, s in enumerate(ctrl.colorSchemes):
        if not s.get("is_active"):
            target_idx = idx
            break
    ctrl.selectScheme(target_idx)
    assert ctrl.selectedSchemeIndex == target_idx
    selected = ctrl.selectedScheme
    assert "name" in selected
    assert "window_bg" in selected

    # Request diff preview
    diff_captured = []
    ctrl.diffPreviewReady.connect(lambda d: diff_captured.append(d))
    ctrl.requestDiffPreview(0)
    assert len(diff_captured) == 1
    assert len(ctrl.currentDiffPreview) > 0

    # Request apply confirmation dialog
    dialog_state = []
    ctrl.confirmDialogVisibilityChanged.connect(lambda v: dialog_state.append(v))
    ctrl.requestApplySelected()
    assert ctrl.showConfirmDialog is True
    assert ctrl.confirmSchemeName != ""

    # Cancel apply
    ctrl.cancelApply()
    assert ctrl.showConfirmDialog is False

    # Confirm apply in safe mode
    results = []
    ctrl.applyFinished.connect(lambda ok, msg, dry: results.append((ok, msg, dry)))
    ctrl.confirmApplySelected()
    assert len(results) == 1
    ok, msg, dry = results[0]
    assert ok is True
    assert dry is True  # In safe mode, dry run is True
    assert "Safe Mode" in msg


def test_desktop_controller_workflow(qapp: QGuiApplication) -> None:
    ctrl = DesktopController()
    assert len(ctrl.presets) == 3
    assert ctrl.detectedLayout is not None
    assert ctrl.draftLayout is not None
    assert ctrl.isDraftModified is False

    # Preset selection
    ctrl.loadPreset("nothing_inspired")
    assert ctrl.selectedPresetId == "nothing_inspired"
    assert ctrl.showWidgets is True
    assert ctrl.panelPosition == "top"
    assert ctrl.dockPosition == "bottom"
    assert ctrl.isDraftModified is True

    # Parameter tweaks
    ctrl.setPanelThickness(40)
    assert ctrl.panelThickness == 40
    ctrl.setDockIconSize(48)
    assert ctrl.dockIconSize == 48

    # Diff preview
    diffs = []
    ctrl.diffPreviewReady.connect(lambda d: diffs.append(d))
    ctrl.requestDiffPreview()
    assert len(diffs) == 1
    assert "Unified Diff Preview" in diffs[0]

    # Modal dialog transitions
    ctrl.requestApplyDraft()
    assert ctrl.showConfirmDialog is True
    ctrl.cancelApply()
    assert ctrl.showConfirmDialog is False

    # Apply in safe mode
    results = []
    ctrl.applyFinished.connect(lambda ok, msg, dry: results.append((ok, msg, dry)))
    ctrl.confirmApplyDraft()
    assert len(results) == 1
    ok, msg, dry = results[0]
    assert ok is True
    assert dry is True
    assert "Safe Mode active" in msg


def test_backup_controller_deletion_and_search(tmp_path: Path, qapp: QGuiApplication) -> None:
    source_dir = tmp_path / "mock_config"
    source_dir.mkdir()
    (source_dir / "kdeglobals").write_text("[General]\nfont=Inter\n")

    backup_dir = tmp_path / "snapshots"
    bm = BackupManager(backup_root=backup_dir, source_config_dir=source_dir)
    ctrl = BackupController(backup_manager=bm)

    assert ctrl.totalSnapshotCount == 0
    assert ctrl.snapshotCount == 0
    assert ctrl.searchQuery == ""

    # Create 3 snapshots
    assert ctrl.createSnapshot("Alpha Snapshot") is True
    assert ctrl.createSnapshot("Beta Snapshot") is True
    assert ctrl.createSnapshot("Gamma Snapshot") is True
    assert ctrl.totalSnapshotCount == 3
    assert ctrl.snapshotCount == 3
    assert len(ctrl.snapshots) == 3

    # Test search query filtering
    ctrl.setSearchQuery("Alpha")
    assert ctrl.snapshotCount == 1
    assert ctrl.totalSnapshotCount == 3
    assert ctrl.snapshots[0]["description"] == "Alpha Snapshot"

    ctrl.setSearchQuery("NonExistent")
    assert ctrl.snapshotCount == 0
    assert ctrl.totalSnapshotCount == 3

    ctrl.setSearchQuery("")
    assert ctrl.snapshotCount == 3
    assert ctrl.totalSnapshotCount == 3

    # Selection and adjacent selection behavior
    selected_target = ctrl.snapshots[1]["id"]
    ctrl.selectSnapshot(selected_target)
    assert ctrl.selectedSnapshotId == selected_target
    assert ctrl.selectedSnapshot["id"] == selected_target

    # Test delete request workflow
    delete_dialog_events = []
    ctrl.deleteConfirmDialogChanged.connect(lambda: delete_dialog_events.append(ctrl.showDeleteConfirmDialog))

    ctrl.requestDeleteSnapshot(selected_target)
    assert ctrl.showDeleteConfirmDialog is True
    assert ctrl.deleteTargetSnapshotId == selected_target
    assert ctrl.deleteTargetDescription == "Beta Snapshot"

    # Test cancel delete
    ctrl.cancelDelete()
    assert ctrl.showDeleteConfirmDialog is False
    assert ctrl.deleteTargetSnapshotId == ""

    # Test confirm delete
    ctrl.requestDeleteSnapshot(selected_target)
    completed_events = []
    ctrl.snapshotOperationCompleted.connect(lambda msg, ok: completed_events.append((msg, ok)))

    ctrl.confirmDelete()
    assert ctrl.showDeleteConfirmDialog is False
    assert len(completed_events) == 1
    assert completed_events[0][1] is True
    assert "deleted" in completed_events[0][0].lower()
    assert ctrl.totalSnapshotCount == 2
    remaining_ids = [s["id"] for s in ctrl.snapshots]
    assert selected_target not in remaining_ids
    # Adjacent selection: should point to a valid remaining snapshot
    assert ctrl.selectedSnapshotId in remaining_ids

    # Test protection against deletion during active transaction/restore
    last_snap_id = ctrl.snapshots[0]["id"]
    ctrl.addProtectedSnapshotId(last_snap_id)
    assert ctrl.deleteSnapshot(last_snap_id) is False
    assert ctrl.totalSnapshotCount == 2

    ctrl.removeProtectedSnapshotId(last_snap_id)
    assert ctrl.deleteSnapshot(last_snap_id) is True
    assert ctrl.totalSnapshotCount == 1

    # Delete the final remaining snapshot
    final_id = ctrl.snapshots[0]["id"]
    assert ctrl.deleteSnapshot(final_id) is True
    assert ctrl.totalSnapshotCount == 0
    assert ctrl.snapshotCount == 0
    assert ctrl.selectedSnapshotId == ""
    assert ctrl.selectedSnapshot == {}


