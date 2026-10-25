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
