"""Application controller managing active navigation view, global state, and status toasts."""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from plasmaforge import __version__


class AppController(QObject):
    """Main application navigation and global state coordinator."""

    activeSectionChanged = Signal(str)
    safeModeChanged = Signal(bool)
    statusToastRequested = Signal(str, str)  # message, level

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._active_section = "Overview"
        self._app_name = "PlasmaForge"
        self._app_version = __version__
        self._safe_mode = True

    @Property(str, notify=activeSectionChanged)
    def activeSection(self) -> str:
        return self._active_section

    @Property(str, constant=True)
    def appName(self) -> str:
        return self._app_name

    @Property(str, constant=True)
    def appVersion(self) -> str:
        return self._app_version

    @Property(bool, notify=safeModeChanged)
    def safeMode(self) -> bool:
        return self._safe_mode

    @Slot(bool)
    def setSafeMode(self, enabled: bool) -> None:
        if self._safe_mode != enabled:
            self._safe_mode = enabled
            self.safeModeChanged.emit(enabled)

    @Slot(str)
    def navigateTo(self, section: str) -> None:
        valid_sections = {
            "Overview",
            "Theme Studio",
            "Desktop Builder",
            "Setup Gallery",
            "Global Themes",
            "Backups & Restore",
            "Settings",
        }
        if section in valid_sections and section != self._active_section:
            self._active_section = section
            self.activeSectionChanged.emit(section)

    @Slot(str, str)
    def showToast(self, message: str, level: str = "info") -> None:
        self.statusToastRequested.emit(message, level)
