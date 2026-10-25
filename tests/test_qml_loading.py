"""Integration test verifying full QML scene graph loading and view instantiations."""

from PySide6.QtGui import QGuiApplication
import pytest

from plasmaforge.main import create_application


@pytest.fixture(scope="session")
def qapp() -> QGuiApplication:
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(["test", "-platform", "offscreen"])
    return app


def test_qml_full_startup(qapp: QGuiApplication) -> None:
    """Verify that main.qml and all subviews load cleanly in QQmlApplicationEngine."""
    app, engine = create_application(["test", "-platform", "offscreen"])
    assert app is not None
    assert engine is not None
    root_objects = engine.rootObjects()
    assert len(root_objects) > 0, "Failed to instantiate QML root ApplicationWindow"

    window = root_objects[0]
    assert window.property("title") == "PlasmaForge - KDE Plasma 6 Customization Studio"

    # Verify controller references
    app_ctrl = engine._controllers["app"]
    assert app_ctrl.activeSection == "Overview"

    # Cycle through all views
    sections = [
        "Overview",
        "Theme Studio",
        "Desktop Builder",
        "Setup Gallery",
        "Backups & Restore",
        "Settings",
    ]
    for section in sections:
        app_ctrl.navigateTo(section)
        assert app_ctrl.activeSection == section

    # Test responsive window resizing (minimum laptop dimensions 800x560 and wide 1440x900)
    window.setProperty("width", 800)
    window.setProperty("height", 560)
    theme_ctrl = engine._controllers["theme"]
    desktop_ctrl = engine._controllers["desktop"]
    backup_ctrl = engine._controllers["backup"]

    for sec in sections:
        app_ctrl.navigateTo(sec)
        assert app_ctrl.activeSection == sec
        app.processEvents()

    # Verify modal dialogs open and cancel cleanly on small screens
    app_ctrl.navigateTo("Theme Studio")
    theme_ctrl.requestApplySelected()
    assert theme_ctrl.showConfirmDialog is True
    app.processEvents()
    theme_ctrl.cancelApply()
    assert theme_ctrl.showConfirmDialog is False
    app.processEvents()

    app_ctrl.navigateTo("Desktop Builder")
    desktop_ctrl.requestApplyDraft()
    assert desktop_ctrl.showConfirmDialog is True
    app.processEvents()
    desktop_ctrl.cancelApply()
    assert desktop_ctrl.showConfirmDialog is False
    app.processEvents()

    app_ctrl.navigateTo("Backups & Restore")
    backup_ctrl.requestDeleteSnapshot("mock_target")
    assert backup_ctrl.showDeleteConfirmDialog is True
    app.processEvents()
    backup_ctrl.cancelDelete()
    assert backup_ctrl.showDeleteConfirmDialog is False
    app.processEvents()

    # Wide screen test
    window.setProperty("width", 1440)
    window.setProperty("height", 900)
    for sec in sections:
        app_ctrl.navigateTo(sec)
        app.processEvents()


