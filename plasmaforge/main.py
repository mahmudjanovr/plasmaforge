"""PlasmaForge application entrypoint and Qt Quick scene graph bootstrap."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
from PySide6.QtQuickControls2 import QQuickStyle

from plasmaforge import __app_name__, __version__
from plasmaforge.controllers import (
    AppController,
    BackupController,
    PresetController,
    SettingsController,
    SystemController,
    ThemeController,
    DesktopController,
)

CONTROLLERS_URI = "PlasmaForge.Controllers"


def create_application(argv: list[str] | None = None) -> tuple[QGuiApplication, QQmlApplicationEngine]:
    """Create and configure QGuiApplication and QQmlApplicationEngine."""
    if argv is None:
        argv = sys.argv

    QCoreApplication.setApplicationName(__app_name__)
    QCoreApplication.setApplicationVersion(__version__)
    QCoreApplication.setOrganizationName("PlasmaForge")
    QCoreApplication.setOrganizationDomain("plasmaforge.org")

    # Set base Qt Quick control style
    QQuickStyle.setStyle("Basic")

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(argv)

    # Instantiate controllers
    app_ctrl = AppController(app)
    system_ctrl = SystemController(app)
    theme_ctrl = ThemeController(app)
    preset_ctrl = PresetController(app)
    backup_ctrl = BackupController(app)
    settings_ctrl = SettingsController(app)
    desktop_ctrl = DesktopController(app)

    # Register controllers as first-class QML singletons
    qmlRegisterSingletonInstance(AppController, CONTROLLERS_URI, 1, 0, "AppCtrl", app_ctrl)
    qmlRegisterSingletonInstance(SystemController, CONTROLLERS_URI, 1, 0, "SystemCtrl", system_ctrl)
    qmlRegisterSingletonInstance(ThemeController, CONTROLLERS_URI, 1, 0, "ThemeCtrl", theme_ctrl)
    qmlRegisterSingletonInstance(PresetController, CONTROLLERS_URI, 1, 0, "PresetCtrl", preset_ctrl)
    qmlRegisterSingletonInstance(BackupController, CONTROLLERS_URI, 1, 0, "BackupCtrl", backup_ctrl)
    qmlRegisterSingletonInstance(SettingsController, CONTROLLERS_URI, 1, 0, "SettingsCtrl", settings_ctrl)
    qmlRegisterSingletonInstance(DesktopController, CONTROLLERS_URI, 1, 0, "DesktopCtrl", desktop_ctrl)

    # Wire safe mode synchronization & toasts
    app_ctrl.setSafeMode(settings_ctrl.safeMode)
    settings_ctrl.safeModeChanged.connect(
        lambda: app_ctrl.setSafeMode(settings_ctrl.safeMode)
    )
    theme_ctrl.applyFinished.connect(
        lambda ok, msg, dry: (
            system_ctrl.refresh(),
            app_ctrl.showToast(msg, "info" if dry else ("success" if ok else "error")),
        )
    )
    theme_ctrl.restoreFinished.connect(
        lambda ok, msg: (
            system_ctrl.refresh(),
            app_ctrl.showToast(msg, "success" if ok else "error"),
        )
    )
    backup_ctrl.snapshotOperationCompleted.connect(
        lambda msg, ok: (
            system_ctrl.refresh(),
            app_ctrl.showToast(msg, "success" if ok else "error"),
        )
    )
    desktop_ctrl.applyFinished.connect(
        lambda ok, msg, dry: (
            system_ctrl.refresh(),
            app_ctrl.showToast(msg, "info" if dry else ("success" if ok else "error")),
        )
    )
    desktop_ctrl.restoreFinished.connect(
        lambda ok, msg: (
            system_ctrl.refresh(),
            app_ctrl.showToast(msg, "success" if ok else "error"),
        )
    )
    preset_ctrl.layoutTransferRequested.connect(
        lambda layout: (
            desktop_ctrl.loadDraftFromDict(layout),
            app_ctrl.navigateTo("Desktop Builder"),
            app_ctrl.showToast("Loaded layout into Desktop Builder draft.", "info"),
        )
    )
    preset_ctrl.themeTransferRequested.connect(
        lambda scheme_id: (
            theme_ctrl.selectSchemeById(scheme_id),
            app_ctrl.navigateTo("Theme Studio"),
            app_ctrl.showToast("Selected color scheme in Theme Studio.", "info"),
        )
    )
    preset_ctrl.profileOperationCompleted.connect(
        lambda msg, ok: (
            app_ctrl.showToast(msg, "success" if ok else "error")
        )
    )


    engine = QQmlApplicationEngine()

    # Add QML import paths
    qml_dir = Path(__file__).resolve().parent / "qml"
    engine.addImportPath(str(qml_dir.parent.parent))
    engine.addImportPath(str(qml_dir))

    # Also bind to root context for compatibility
    ctx = engine.rootContext()
    ctx.setContextProperty("appCtrl", app_ctrl)
    ctx.setContextProperty("systemCtrl", system_ctrl)
    ctx.setContextProperty("themeCtrl", theme_ctrl)
    ctx.setContextProperty("presetCtrl", preset_ctrl)
    ctx.setContextProperty("backupCtrl", backup_ctrl)
    ctx.setContextProperty("settingsCtrl", settings_ctrl)
    ctx.setContextProperty("desktopCtrl", desktop_ctrl)

    # Keep references alive
    engine._controllers = {  # type: ignore[attr-defined]
        "app": app_ctrl,
        "system": system_ctrl,
        "theme": theme_ctrl,
        "preset": preset_ctrl,
        "backup": backup_ctrl,
        "settings": settings_ctrl,
        "desktop": desktop_ctrl,
    }

    main_qml_path = qml_dir / "main.qml"
    engine.load(str(main_qml_path))

    if not engine.rootObjects():
        raise RuntimeError(f"Failed to load QML root object from {main_qml_path}")

    return app, engine


def main() -> int:
    """CLI launcher for PlasmaForge."""
    parser = argparse.ArgumentParser(
        prog="plasmaforge",
        description="PlasmaForge - Native Linux desktop customization studio for KDE Plasma 6",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{__app_name__} {__version__}",
    )
    parser.add_argument(
        "--offscreen",
        action="store_true",
        help="Run Qt in offscreen mode (for testing / headless validation)",
    )
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        default=True,
        help="Enforce Phase 1 read-only safety mode (enabled by default)",
    )

    args, unknown = parser.parse_known_args()

    argv = [sys.argv[0]] + unknown
    if args.offscreen:
        argv.extend(["-platform", "offscreen"])

    try:
        app, engine = create_application(argv)
    except Exception as e:
        sys.stderr.write(f"PlasmaForge startup error: {e}\n")
        return 1

    if args.offscreen:
        print("PlasmaForge offscreen startup check passed successfully.")
        return 0

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
