"""Theme controller coordinating color schemes, live apply, diff inspection, safe restore, and reactive Theme Studio engine."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from plasmaforge.core.color_scheme_applier import ApplyResult, KdeColorSchemeApplier
from plasmaforge.core.config import get_config, save_config
from plasmaforge.core.theme_presets import (
    HEX_COLOR_PATTERN,
    ThemeColors,
    ThemePreset,
    ThemePresetManager,
    ThemeTypography,
    slugify_name,
)
from plasmaforge.core.themes import ThemeInspector, detect_active_color_scheme


class ThemeController(QObject):
    """Coordinates KDE color schemes, reactive theme draft editing, live preview, and persistent JSON presets."""

    schemesChanged = Signal()
    stylesChanged = Signal()
    selectedSchemeChanged = Signal()
    activeSchemeChanged = Signal()
    applyFinished = Signal(bool, str, bool)  # success, message, is_dry_run
    restoreFinished = Signal(bool, str)     # success, message
    diffPreviewReady = Signal(str)
    confirmDialogVisibilityChanged = Signal(bool)
    restoreStateChanged = Signal()

    # Reactive Theme Studio Engine signals
    themeDraftChanged = Signal()
    presetsListChanged = Signal()
    presetDialogStateChanged = Signal()
    presetOperationCompleted = Signal(str, bool)  # message, success

    def __init__(self, parent: QObject | None = None, storage_dir: Optional[Path] = None) -> None:
        super().__init__(parent)
        self._config = get_config()
        self._inspector = ThemeInspector()
        self._applier = KdeColorSchemeApplier(safe_mode=self._config.safe_mode)
        self._preset_manager = ThemePresetManager(storage_dir=storage_dir)

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

        # Reactive Theme Draft State
        self._primary_color: str = "#14b8a6"
        self._background_color: str = "#131518"
        self._surface_color: str = "#181b20"
        self._text_color: str = "#f3f4f6"
        self._secondary_text_color: str = "#9ca3af"
        self._font_family: str = "Inter"
        self._font_size: int = 13
        self._border_radius: int = 6
        self._spacing_scale: float = 1.0

        self._current_preset_id: str = "plasmaforge_teal"
        self._current_preset_name: str = "PlasmaForge Teal (Default)"
        self._is_draft_modified: bool = False

        # Preset dialogs state
        self._show_preset_save_dialog: bool = False
        self._preset_save_dialog_mode: str = "save_new"  # "save_new" or "overwrite"
        self._show_preset_delete_dialog: bool = False
        self._delete_target_preset_id: str = ""
        self._delete_target_preset_name: str = ""

        self.refresh()
        self._init_draft_from_default()

    def _init_draft_from_default(self) -> None:
        """Initialize draft state from the default preset."""
        default_preset = self._preset_manager.get_preset("plasmaforge_teal")
        if default_preset:
            self._primary_color = default_preset.colors.primary
            self._background_color = default_preset.colors.background
            self._surface_color = default_preset.colors.surface
            self._text_color = default_preset.colors.text
            self._secondary_text_color = default_preset.colors.secondary_text
            self._font_family = default_preset.typography.font_family
            self._font_size = default_preset.typography.font_size
            self._border_radius = default_preset.border_radius
            self._spacing_scale = default_preset.spacing_scale
            self._current_preset_id = default_preset.id
            self._current_preset_name = default_preset.name
            self._is_draft_modified = False

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

    # ==========================================
    # KDE Color Schemes Properties & Slots
    # ==========================================
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

    # ==========================================
    # Reactive Theme Studio Properties
    # ==========================================
    @Property(str, notify=themeDraftChanged)
    def primaryColor(self) -> str:
        return self._primary_color

    @Property(str, notify=themeDraftChanged)
    def backgroundColor(self) -> str:
        return self._background_color

    @Property(str, notify=themeDraftChanged)
    def surfaceColor(self) -> str:
        return self._surface_color

    @Property(str, notify=themeDraftChanged)
    def textColor(self) -> str:
        return self._text_color

    @Property(str, notify=themeDraftChanged)
    def secondaryTextColor(self) -> str:
        return self._secondary_text_color

    @Property(str, notify=themeDraftChanged)
    def fontFamily(self) -> str:
        return self._font_family

    @Property(int, notify=themeDraftChanged)
    def fontSize(self) -> int:
        return self._font_size

    @Property(int, notify=themeDraftChanged)
    def borderRadius(self) -> int:
        return self._border_radius

    @Property(float, notify=themeDraftChanged)
    def spacingScale(self) -> float:
        return self._spacing_scale

    # Derived responsive geometry for QML bindings
    @Property(int, notify=themeDraftChanged)
    def spacingXs(self) -> int:
        return max(2, int(round(4 * self._spacing_scale)))

    @Property(int, notify=themeDraftChanged)
    def spacingSm(self) -> int:
        return max(4, int(round(8 * self._spacing_scale)))

    @Property(int, notify=themeDraftChanged)
    def spacingMd(self) -> int:
        return max(6, int(round(12 * self._spacing_scale)))

    @Property(int, notify=themeDraftChanged)
    def spacingLg(self) -> int:
        return max(8, int(round(16 * self._spacing_scale)))

    @Property(int, notify=themeDraftChanged)
    def spacingXl(self) -> int:
        return max(10, int(round(20 * self._spacing_scale)))

    @Property(int, notify=themeDraftChanged)
    def spacingXxl(self) -> int:
        return max(14, int(round(24 * self._spacing_scale)))

    @Property(int, notify=themeDraftChanged)
    def radiusSm(self) -> int:
        return max(0, self._border_radius - 2)

    @Property(int, notify=themeDraftChanged)
    def radiusMd(self) -> int:
        return self._border_radius

    @Property(int, notify=themeDraftChanged)
    def radiusLg(self) -> int:
        return self._border_radius + 2

    @Property(int, notify=themeDraftChanged)
    def radiusXl(self) -> int:
        return self._border_radius + 6

    @Property(str, notify=themeDraftChanged)
    def currentPresetId(self) -> str:
        return self._current_preset_id

    @Property(str, notify=themeDraftChanged)
    def currentPresetName(self) -> str:
        return self._current_preset_name

    @Property(bool, notify=themeDraftChanged)
    def isDraftModified(self) -> bool:
        return self._is_draft_modified

    @Property(bool, notify=themeDraftChanged)
    def isCurrentPresetBuiltin(self) -> bool:
        preset = self._preset_manager.get_preset(self._current_preset_id)
        return bool(preset and preset.is_builtin)

    @Property("QVariantList", notify=presetsListChanged)
    def themePresets(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._preset_manager.list_presets()]

    @Property("QVariantList", constant=True)
    def availableFontFamilies(self) -> List[str]:
        return ["Inter", "Noto Sans", "Cantarell", "JetBrains Mono", "Sans Serif"]

    @Property("QVariantList", constant=True)
    def availableFontSizes(self) -> List[int]:
        return [11, 12, 13, 14, 16]

    @Property("QVariantList", constant=True)
    def availableRadiusOptions(self) -> List[int]:
        return [0, 4, 6, 8, 12, 16]

    @Property("QVariantList", constant=True)
    def availableSpacingOptions(self) -> List[float]:
        return [0.75, 0.85, 1.0, 1.15, 1.25, 1.5]

    @Property(bool, notify=presetDialogStateChanged)
    def showPresetSaveDialog(self) -> bool:
        return self._show_preset_save_dialog

    @Property(str, notify=presetDialogStateChanged)
    def presetSaveDialogMode(self) -> str:
        return self._preset_save_dialog_mode

    @Property(bool, notify=presetDialogStateChanged)
    def showPresetDeleteDialog(self) -> bool:
        return self._show_preset_delete_dialog

    @Property(str, notify=presetDialogStateChanged)
    def deleteTargetPresetId(self) -> str:
        return self._delete_target_preset_id

    @Property(str, notify=presetDialogStateChanged)
    def deleteTargetPresetName(self) -> str:
        return self._delete_target_preset_name

    # ==========================================
    # Theme Controls Slots
    # ==========================================
    @Slot(str)
    def setPrimaryColor(self, color_hex: str) -> None:
        val = color_hex.strip()
        if HEX_COLOR_PATTERN.match(val):
            if self._primary_color != val:
                self._primary_color = val
                self._is_draft_modified = True
                self.themeDraftChanged.emit()

    @Slot(str)
    def setBackgroundColor(self, color_hex: str) -> None:
        val = color_hex.strip()
        if HEX_COLOR_PATTERN.match(val):
            if self._background_color != val:
                self._background_color = val
                self._is_draft_modified = True
                self.themeDraftChanged.emit()

    @Slot(str)
    def setSurfaceColor(self, color_hex: str) -> None:
        val = color_hex.strip()
        if HEX_COLOR_PATTERN.match(val):
            if self._surface_color != val:
                self._surface_color = val
                self._is_draft_modified = True
                self.themeDraftChanged.emit()

    @Slot(str)
    def setTextColor(self, color_hex: str) -> None:
        val = color_hex.strip()
        if HEX_COLOR_PATTERN.match(val):
            if self._text_color != val:
                self._text_color = val
                self._is_draft_modified = True
                self.themeDraftChanged.emit()

    @Slot(str)
    def setSecondaryTextColor(self, color_hex: str) -> None:
        val = color_hex.strip()
        if HEX_COLOR_PATTERN.match(val):
            if self._secondary_text_color != val:
                self._secondary_text_color = val
                self._is_draft_modified = True
                self.themeDraftChanged.emit()

    @Slot(str)
    def setFontFamily(self, family: str) -> None:
        val = family.strip()
        if val and self._font_family != val:
            self._font_family = val
            self._is_draft_modified = True
            self.themeDraftChanged.emit()

    @Slot(int)
    def setFontSize(self, size: int) -> None:
        val = max(9, min(24, size))
        if self._font_size != val:
            self._font_size = val
            self._is_draft_modified = True
            self.themeDraftChanged.emit()

    @Slot(int)
    def setBorderRadius(self, radius: int) -> None:
        val = max(0, min(32, radius))
        if self._border_radius != val:
            self._border_radius = val
            self._is_draft_modified = True
            self.themeDraftChanged.emit()

    @Slot(float)
    def setSpacingScale(self, scale: float) -> None:
        val = max(0.5, min(2.5, round(scale, 2)))
        if abs(self._spacing_scale - val) > 0.001:
            self._spacing_scale = val
            self._is_draft_modified = True
            self.themeDraftChanged.emit()

    # ==========================================
    # Theme Presets Management Slots
    # ==========================================
    @Slot(str, result=bool)
    def loadPreset(self, preset_id: str) -> bool:
        """Load an existing preset into the reactive Theme Studio draft."""
        preset = self._preset_manager.get_preset(preset_id)
        if not preset:
            self.presetOperationCompleted.emit(f"Preset '{preset_id}' not found.", False)
            return False

        self._primary_color = preset.colors.primary
        self._background_color = preset.colors.background
        self._surface_color = preset.colors.surface
        self._text_color = preset.colors.text
        self._secondary_text_color = preset.colors.secondary_text
        self._font_family = preset.typography.font_family
        self._font_size = preset.typography.font_size
        self._border_radius = preset.border_radius
        self._spacing_scale = preset.spacing_scale
        self._current_preset_id = preset.id
        self._current_preset_name = preset.name
        self._is_draft_modified = False

        self.themeDraftChanged.emit()
        self.presetOperationCompleted.emit(f"Loaded preset '{preset.name}'.", True)
        return True

    @Slot()
    def restoreDefaultTheme(self) -> None:
        """Reset the Theme Studio editor to the default PlasmaForge theme values."""
        self.loadPreset("plasmaforge_teal")

    @Slot()
    def requestSavePreset(self) -> None:
        """Open the modal dialog to save current theme as a named preset."""
        self._preset_save_dialog_mode = "save_new"
        self._show_preset_save_dialog = True
        self.presetDialogStateChanged.emit()

    @Slot(str)
    def requestOverwritePreset(self, preset_id: str = "") -> None:
        """Open confirmation dialog to update an existing user preset."""
        target_id = preset_id or self._current_preset_id
        preset = self._preset_manager.get_preset(target_id)
        if preset and preset.is_builtin:
            self.presetOperationCompleted.emit(
                "Cannot overwrite built-in presets. Please save as a new preset.",
                False,
            )
            return
        self._preset_save_dialog_mode = "overwrite"
        self._show_preset_save_dialog = True
        self.presetDialogStateChanged.emit()

    @Slot()
    def cancelSavePreset(self) -> None:
        """Cancel preset save/overwrite dialog."""
        self._show_preset_save_dialog = False
        self.presetDialogStateChanged.emit()

    @Slot(str, bool, result=bool)
    def confirmSavePreset(self, name: str, overwrite: bool = False) -> bool:
        """Save the current theme state as a named JSON preset with optional overwrite."""
        name_clean = name.strip()
        if not name_clean:
            self.presetOperationCompleted.emit("Preset name cannot be empty.", False)
            return False

        preset_id = slugify_name(name_clean)

        # Built-in protection
        builtin_preset = self._preset_manager.get_preset(preset_id)
        if builtin_preset and builtin_preset.is_builtin:
            preset_id = f"{preset_id}_user"

        preset = ThemePreset(
            id=preset_id,
            name=name_clean,
            description=f"User-created theme preset ({name_clean})",
            colors=ThemeColors(
                primary=self._primary_color,
                background=self._background_color,
                surface=self._surface_color,
                text=self._text_color,
                secondary_text=self._secondary_text_color,
            ),
            typography=ThemeTypography(
                font_family=self._font_family,
                font_size=self._font_size,
            ),
            border_radius=self._border_radius,
            spacing_scale=self._spacing_scale,
            is_builtin=False,
        )

        ok, msg = self._preset_manager.save_preset(preset, overwrite=overwrite)
        self._show_preset_save_dialog = False
        self.presetDialogStateChanged.emit()
        self.presetOperationCompleted.emit(msg, ok)

        if ok:
            self._current_preset_id = preset.id
            self._current_preset_name = preset.name
            self._is_draft_modified = False
            self.themeDraftChanged.emit()
            self.presetsListChanged.emit()

        return ok

    @Slot(str)
    def requestDeletePreset(self, preset_id: str) -> None:
        """Prompt confirmation to delete a user preset."""
        preset = self._preset_manager.get_preset(preset_id)
        if not preset:
            self.presetOperationCompleted.emit("Preset not found.", False)
            return
        if preset.is_builtin:
            self.presetOperationCompleted.emit("Built-in presets cannot be deleted.", False)
            return

        self._delete_target_preset_id = preset.id
        self._delete_target_preset_name = preset.name
        self._show_preset_delete_dialog = True
        self.presetDialogStateChanged.emit()

    @Slot()
    def cancelDeletePreset(self) -> None:
        """Cancel preset deletion."""
        self._show_preset_delete_dialog = False
        self._delete_target_preset_id = ""
        self._delete_target_preset_name = ""
        self.presetDialogStateChanged.emit()

    @Slot(result=bool)
    def confirmDeletePreset(self) -> bool:
        """Execute deletion of the confirmed preset."""
        target_id = self._delete_target_preset_id
        self._show_preset_delete_dialog = False
        self._delete_target_preset_id = ""
        self._delete_target_preset_name = ""
        self.presetDialogStateChanged.emit()

        if not target_id:
            return False

        ok, msg = self._preset_manager.delete_preset(target_id)
        self.presetOperationCompleted.emit(msg, ok)

        if ok:
            if self._current_preset_id == target_id:
                self.restoreDefaultTheme()
            self.presetsListChanged.emit()

        return ok

    @Slot(str, str, result=bool)
    def exportPresetJson(self, preset_id: str = "", dest_path: str = "") -> bool:
        """Export preset JSON to disk."""
        pid = preset_id.strip() if preset_id.strip() else self._current_preset_id
        if not pid:
            self.presetOperationCompleted.emit("No preset selected for export.", False)
            return False

        dest = Path(dest_path) if dest_path.strip() else (Path.home() / f"{pid}_theme.json")
        ok, msg = self._preset_manager.export_preset(pid, dest)
        self.presetOperationCompleted.emit(msg, ok)
        return ok

    @Slot(str, result=bool)
    def importPresetJson(self, json_str: str) -> bool:
        """Import theme preset from JSON string without modifying KDE configuration."""
        ok, msg, preset = self._preset_manager.import_preset_json(json_str)
        self.presetOperationCompleted.emit(msg, ok)
        if ok and preset:
            self.presetsListChanged.emit()
            self.loadPreset(preset.id)
        return ok

    @Slot(str, result=bool)
    def importPresetFile(self, file_path: str) -> bool:
        """Import theme preset from file path without modifying KDE configuration."""
        ok, msg, preset = self._preset_manager.import_preset_file(Path(file_path))
        self.presetOperationCompleted.emit(msg, ok)
        if ok and preset:
            self.presetsListChanged.emit()
            self.loadPreset(preset.id)
        return ok

    @Slot()
    def applyCurrentKdeSchemeToEditor(self) -> None:
        """Copy active or selected KDE scheme colors into the Theme Editor."""
        cur = self.selectedScheme
        if not cur:
            return

        if cur.get("selection_bg"):
            self.setPrimaryColor(cur["selection_bg"])
        if cur.get("window_bg"):
            self.setBackgroundColor(cur["window_bg"])
        if cur.get("view_bg"):
            self.setSurfaceColor(cur["view_bg"])
        if cur.get("window_fg"):
            self.setTextColor(cur["window_fg"])
        if cur.get("view_fg"):
            self.setSecondaryTextColor(cur["view_fg"])

        scheme_name = str(cur.get("name", "KDE Scheme"))
        self._current_preset_id = f"kde_{slugify_name(scheme_name)}"
        self._current_preset_name = f"{scheme_name} (Imported)"
        self._is_draft_modified = True
        self.themeDraftChanged.emit()
        self.presetOperationCompleted.emit(f"Imported '{scheme_name}' colors into Theme Editor.", True)
