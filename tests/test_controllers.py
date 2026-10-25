"""Tests for application controllers."""

from PySide6.QtGui import QGuiApplication
import pytest

from plasmaforge.controllers import (
    AppController,
    BackupController,
    PresetController,
    SettingsController,
    SystemController,
    ThemeController,
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
