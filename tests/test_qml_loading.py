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
    for section in [
        "Overview",
        "Theme Studio",
        "Desktop Builder",
        "Setup Gallery",
        "Backups & Restore",
        "Settings",
    ]:
        app_ctrl.navigateTo(section)
        assert app_ctrl.activeSection == section
