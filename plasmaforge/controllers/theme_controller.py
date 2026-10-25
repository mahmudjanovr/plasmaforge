"""Theme controller coordinating color schemes, live apply, diff inspection, and safe restore."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from plasmaforge.core.color_scheme_applier import ApplyResult, KdeColorSchemeApplier
from plasmaforge.core.config import get_config, save_config
from plasmaforge.core.themes import ThemeInspector, detect_active_color_scheme


class ThemeController(QObject):
    """Coordinates color schemes, active status, dry-run diffs, apply workflow, and rollback."""

    schemesChanged = Signal()
    stylesChanged = Signal()
    selectedSchemeChanged = Signal()
    activeSchemeChanged = Signal()
    applyFinished = Signal(bool, str, bool)  # success, message, is_dry_run
    restoreFinished = Signal(bool, str)     # success, message
    diffPreviewReady = Signal(str)
    confirmDialogVisibilityChanged = Signal(bool)
    restoreStateChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = get_config()
        self._inspector = ThemeInspector()
        self._applier = KdeColorSchemeApplier(safe_mode=self._config.safe_mode)

        self._schemes: List[Dict[str, Any]] = []
        self._styles: List[Dict[str, Any]] = []
        self._selected_scheme_index = 0
        self._active_scheme_id = "BreezeDark"

        self._is_applying = False
        self._show_confirm_dialog = False
        self._confirm_scheme_name = ""
        self._confirm_scheme_id = ""
        self._current_diff_preview = ""

        # Restore tracking
        self._last_backup_id = self._config.last_backup_id
        self._previous_scheme_id = self._config.previous_scheme_id

        self.refresh()

    @Slot()
    def refresh(self) -> None:
        """Scan system and user paths for installed themes and detect active color scheme."""
        self._active_scheme_id = detect_active_color_scheme()
        self._schemes = [s.to_dict() for s in self._inspector.get_color_schemes()]
        self._styles = [st.to_dict() for st in self._inspector.get_plasma_styles()]

        if not self._schemes:
            # Fallback mock for testing in minimal isolated test environments
            self._schemes = [
                {
                    "id": "BreezeDark",
                    "name": "Breeze Dark",
                    "file_path": "/usr/share/color-schemes/BreezeDark.colors",
                    "is_user_scheme": False,
                    "window_bg": "#202326",
                    "window_fg": "#fcfcfc",
                    "view_bg": "#181a1d",
                    "view_fg": "#fcfcfc",
                    "selection_bg": "#3daee9",
                    "selection_fg": "#ffffff",
                    "button_bg": "#2d3136",
                    "button_fg": "#fcfcfc",
                    "is_active": True,
                }
            ]

        # Ensure index in range
        if self._selected_scheme_index >= len(self._schemes):
            self._selected_scheme_index = 0

        self.schemesChanged.emit()
        self.stylesChanged.emit()
        self.selectedSchemeChanged.emit()
        self.activeSchemeChanged.emit()

    @Property("QVariantList", notify=schemesChanged)
    def colorSchemes(self) -> List[Dict[str, Any]]:
        return self._schemes

    @Property("QVariantList", notify=stylesChanged)
    def plasmaStyles(self) -> List[Dict[str, Any]]:
        return self._styles

    @Property(str, notify=activeSchemeChanged)
    def activeSchemeId(self) -> str:
        return self._active_scheme_id

    @Property("QVariantMap", notify=selectedSchemeChanged)
    def selectedScheme(self) -> Dict[str, Any]:
        if 0 <= self._selected_scheme_index < len(self._schemes):
            return self._schemes[self._selected_scheme_index]
        return self._schemes[0] if self._schemes else {}

    @Property(int, notify=selectedSchemeChanged)
    def selectedSchemeIndex(self) -> int:
        return self._selected_scheme_index

    @Property(bool, notify=applyFinished)
    def isApplying(self) -> bool:
        return self._is_applying

    @Property(bool, notify=confirmDialogVisibilityChanged)
    def showConfirmDialog(self) -> bool:
        return self._show_confirm_dialog

    @Property(str, notify=confirmDialogVisibilityChanged)
    def confirmSchemeName(self) -> str:
        return self._confirm_scheme_name

    @Property(str, notify=confirmDialogVisibilityChanged)
    def confirmSchemeId(self) -> str:
        return self._confirm_scheme_id

    @Property(str, notify=diffPreviewReady)
    def currentDiffPreview(self) -> str:
        return self._current_diff_preview

    @Property(bool, notify=restoreStateChanged)
    def canRestorePrevious(self) -> bool:
        return bool(self._last_backup_id and self._previous_scheme_id)

    @Property(str, notify=restoreStateChanged)
    def previousSchemeId(self) -> str:
        return self._previous_scheme_id

    @Property(str, notify=restoreStateChanged)
    def lastBackupId(self) -> str:
        return self._last_backup_id

    @Slot(int)
    def selectScheme(self, index: int) -> None:
        if 0 <= index < len(self._schemes) and index != self._selected_scheme_index:
            self._selected_scheme_index = index
            self.selectedSchemeChanged.emit()

    @Slot(str, result=bool)
    def selectSchemeById(self, scheme_id: str) -> bool:
        """Find scheme by ID and select it."""
        for idx, s in enumerate(self._schemes):
            if s.get("id", "").lower() == scheme_id.lower() or s.get("name", "").lower() == scheme_id.lower():
                self.selectScheme(idx)
                return True
        return False

    @Slot(int)
    def requestDiffPreview(self, index: int) -> None:
        """Generate unified diff showing changes between active configuration and target scheme."""
        if 0 <= index < len(self._schemes):
            target = self._schemes[index]
            diff = self._applier.generate_diff_preview(target["id"])
            self._current_diff_preview = diff
            self.diffPreviewReady.emit(diff)

    @Slot()
    def requestApplySelected(self) -> None:
        """Open the apply confirmation dialog identifying target scheme and intended changes."""
        cur = self.selectedScheme
        if not cur:
            return
        self._confirm_scheme_name = str(cur.get("name", "Unknown"))
        self._confirm_scheme_id = str(cur.get("id", ""))
        self._current_diff_preview = self._applier.generate_diff_preview(self._confirm_scheme_id)
        self._show_confirm_dialog = True
        self.confirmDialogVisibilityChanged.emit(True)
        self.diffPreviewReady.emit(self._current_diff_preview)

    @Slot()
    def cancelApply(self) -> None:
        """Cancel confirmation dialog."""
        self._show_confirm_dialog = False
        self.confirmDialogVisibilityChanged.emit(False)

    @Slot()
    def confirmApplySelected(self) -> None:
        """Execute color scheme application with backup and safety checks."""
        self._show_confirm_dialog = False
        self.confirmDialogVisibilityChanged.emit(False)

        scheme_id = self._confirm_scheme_id
        if not scheme_id:
            cur = self.selectedScheme
            scheme_id = str(cur.get("id", ""))

        if not scheme_id:
            self.applyFinished.emit(False, "No scheme selected for application.", False)
            return

        self._is_applying = True

        # Check latest safe mode setting from config
        config = get_config()
        self._applier.safe_mode = config.safe_mode

        # Save previous scheme for restore if in live mode
        prev_scheme = self._active_scheme_id

        result: ApplyResult = self._applier.apply_scheme(scheme_id)
        self._is_applying = False

        if result.success and not result.is_dry_run:
            # Live mode apply succeeded
            self._last_backup_id = result.backup_id
            self._previous_scheme_id = prev_scheme
            config.last_backup_id = result.backup_id
            config.previous_scheme_id = prev_scheme
            save_config(config)
            self.restoreStateChanged.emit()

            # Refresh system state and theme list
            self.refresh()

        self.applyFinished.emit(result.success, result.message, result.is_dry_run)

    @Slot()
    def restorePreviousScheme(self) -> None:
        """Safely restore the pre-apply backup and re-apply previous scheme."""
        if not self._last_backup_id:
            self.restoreFinished.emit(False, "No pre-apply backup recorded to restore.")
            return

        ok, msg = self._applier.restore_backup(
            self._last_backup_id,
            self._previous_scheme_id,
        )

        if ok:
            # Clear previous restore state after successful restore
            config = get_config()
            config.last_backup_id = ""
            config.previous_scheme_id = ""
            save_config(config)

            self._last_backup_id = ""
            self._previous_scheme_id = ""
            self.restoreStateChanged.emit()
            self.refresh()

        self.restoreFinished.emit(ok, msg)
