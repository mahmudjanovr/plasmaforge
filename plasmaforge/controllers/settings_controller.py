"""Settings controller exposing user preferences and Phase 1 safety constraints."""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from plasmaforge.core.config import AppConfig, get_config, save_config


class SettingsController(QObject):
    """Coordinates application preferences and enforces Phase 1 safety restrictions."""

    settingsChanged = Signal()
    saveNotification = Signal(str, bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config: AppConfig = get_config()

    @Property(bool, constant=True)
    def safeMode(self) -> bool:
        # Phase 1: Always True, cannot be disabled via UI
        return True

    @Property(bool, notify=settingsChanged)
    def dryRun(self) -> bool:
        return self._config.dry_run

    @Property(str, notify=settingsChanged)
    def backupDir(self) -> str:
        return self._config.backup_dir

    @Property(str, notify=settingsChanged)
    def themeMode(self) -> str:
        return self._config.theme_mode

    @Property(bool, notify=settingsChanged)
    def enableAnimations(self) -> bool:
        return self._config.enable_animations

    @Property(bool, notify=settingsChanged)
    def autoBackupOnPreview(self) -> bool:
        return self._config.auto_backup_on_preview

    @Slot(str)
    def setBackupDir(self, path: str) -> None:
        clean = path.strip()
        if clean and clean != self._config.backup_dir:
            self._config.backup_dir = clean
            save_config(self._config)
            self.settingsChanged.emit()
            self.saveNotification.emit("Backup directory updated.", True)

    @Slot(str)
    def setThemeMode(self, mode: str) -> None:
        if mode in {"dark", "light", "system"} and mode != self._config.theme_mode:
            self._config.theme_mode = mode
            save_config(self._config)
            self.settingsChanged.emit()
            self.saveNotification.emit("Theme preference updated.", True)

    @Slot(bool)
    def setEnableAnimations(self, enabled: bool) -> None:
        if enabled != self._config.enable_animations:
            self._config.enable_animations = enabled
            save_config(self._config)
            self.settingsChanged.emit()
            self.saveNotification.emit("Animation preference updated.", True)

    @Slot(bool)
    def setAutoBackupOnPreview(self, enabled: bool) -> None:
        if enabled != self._config.auto_backup_on_preview:
            self._config.auto_backup_on_preview = enabled
            save_config(self._config)
            self.settingsChanged.emit()
            self.saveNotification.emit("Auto-backup preference updated.", True)
