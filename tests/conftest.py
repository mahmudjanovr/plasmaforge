"""Pytest shared fixtures."""

import pytest
from PySide6.QtGui import QGuiApplication


@pytest.fixture(scope="session")
def qapp() -> QGuiApplication:
    """Session-wide offscreen QGuiApplication fixture."""
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(["test", "-platform", "offscreen"])
    return app
