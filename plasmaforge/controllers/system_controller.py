"""System controller exposing KDE Plasma 6 environment state to QML."""

from __future__ import annotations

from typing import Any, Dict

from PySide6.QtCore import Property, QObject, Signal, Slot

from plasmaforge.core.system_info import SystemInfo, get_system_info


class SystemController(QObject):
    """Exposes system metrics and KDE environment status to QML."""

    systemInfoChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._info: SystemInfo = get_system_info()

    @Slot()
    def refresh(self) -> None:
        self._info = get_system_info()
        self.systemInfoChanged.emit()

    @Property(str, notify=systemInfoChanged)
    def plasmaVersion(self) -> str:
        return self._info.plasma_version

    @Property(str, notify=systemInfoChanged)
    def qtVersion(self) -> str:
        return self._info.qt_version

    @Property(str, notify=systemInfoChanged)
    def sessionType(self) -> str:
        return self._info.session_type.capitalize()

    @Property(str, notify=systemInfoChanged)
    def desktopEnvironment(self) -> str:
        return self._info.desktop_environment

    @Property(str, notify=systemInfoChanged)
    def distribution(self) -> str:
        return self._info.distribution

    @Property(str, notify=systemInfoChanged)
    def kernelVersion(self) -> str:
        return self._info.kernel_version

    @Property(str, notify=systemInfoChanged)
    def architecture(self) -> str:
        return self._info.architecture

    @Property(str, notify=systemInfoChanged)
    def activeLookAndFeel(self) -> str:
        return self._info.active_look_and_feel

    @Property(str, notify=systemInfoChanged)
    def activeFont(self) -> str:
        return self._info.active_font

    @Property(str, notify=systemInfoChanged)
    def activeFixedFont(self) -> str:
        return self._info.active_fixed_font

    @Property(bool, notify=systemInfoChanged)
    def isPlasma6(self) -> bool:
        return self._info.is_plasma_6

    @Property(bool, notify=systemInfoChanged)
    def safeModeActive(self) -> bool:
        return self._info.safe_mode_active

    @Property("QVariantMap", notify=systemInfoChanged)
    def toolsAvailable(self) -> Dict[str, Any]:
        return self._info.tools_available
