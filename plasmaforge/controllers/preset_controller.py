"""Preset and profile controller coordinating Setup Gallery browsing, filtering, import/export, and workbench transfers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from plasmaforge.core.adapter_boundary import DryRunAdapter
from plasmaforge.core.presets import get_all_presets
from plasmaforge.core.profiles import ProfileManager, SetupProfile


class PresetController(QObject):
    """Coordinates Setup Gallery profiles, category filtering, search, import/export, and dry-run inspections."""

    profilesChanged = Signal()
    selectedProfileChanged = Signal()
    categoryChanged = Signal()
    searchQueryChanged = Signal()
    previewChanged = Signal()
    profileOperationCompleted = Signal(str, bool)  # message, success
    layoutTransferRequested = Signal("QVariantMap")
    themeTransferRequested = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._profile_manager = ProfileManager()
        self._legacy_presets = get_all_presets()
        self._dry_run_adapter = DryRunAdapter(safe_mode=True)

        self._all_profiles: List[SetupProfile] = []
        self._filtered_profiles: List[Dict[str, Any]] = []
        self._selected_index = 0
        self._selected_category = "All"
        self._search_query = ""
        self._current_preview = ""

        self.refresh()

    @Slot()
    def refresh(self) -> None:
        """Reload profiles from manager and apply current filters."""
        self._all_profiles = self._profile_manager.list_profiles()
        self._apply_filter()

    def _apply_filter(self) -> None:
        """Filter profiles by active category and search query."""
        results: List[SetupProfile] = []
        q = self._search_query.strip().lower()

        for p in self._all_profiles:
            # Category match
            if self._selected_category != "All":
                if self._selected_category == "Imported":
                    if not p.is_user_imported:
                        continue
                elif p.category.lower() != self._selected_category.lower():
                    continue

            # Search query match
            if q:
                match_name = q in p.name.lower()
                match_desc = q in p.description.lower()
                match_tag = any(q in t.lower() for t in p.tags)
                match_cat = q in p.category.lower()
                if not (match_name or match_desc or match_tag or match_cat):
                    continue

            results.append(p)

        self._filtered_profiles = [p.to_dict() for p in results]

        # Reset or clamp selected index
        if self._selected_index >= len(self._filtered_profiles):
            self._selected_index = 0

        self.profilesChanged.emit()
        self.selectedProfileChanged.emit()
        self._update_preview()

    def _update_preview(self) -> None:
        if 0 <= self._selected_index < len(self._filtered_profiles):
            p = self._filtered_profiles[self._selected_index]
            # Generate diff description for selected profile
            lines = [
                f"# Dry-Run Configuration Changeset Preview: {p.get('name')}",
                f"# Setup Gallery Profile: {p.get('name')}",
                f"# Author: {p.get('author')} (v{p.get('version')})",
                f"# Category: {p.get('category')}",
                f"# Color Scheme: {p.get('color_scheme', {}).get('name')}",
                f"# Top Panel: {p.get('desktop_layout', {}).get('top_panel', {}).get('position')} ({p.get('desktop_layout', {}).get('top_panel', {}).get('thickness')}px)",
                f"# Dock: {p.get('desktop_layout', {}).get('dock', {}).get('position')} ({p.get('desktop_layout', {}).get('dock', {}).get('thickness')}px)",
                "--------------------------------------------------",
                "",
                "# Live-Applicable Changes:",
                f"  ~/.config/kdeglobals: ColorScheme = {p.get('color_scheme', {}).get('scheme_id')}",
                f"  ~/.config/plasma-org.kde.plasma.desktop-appletsrc: Top Panel Position = {p.get('desktop_layout', {}).get('top_panel', {}).get('position')}",
                f"  ~/.config/plasma-org.kde.plasma.desktop-appletsrc: Dock Position = {p.get('desktop_layout', {}).get('dock', {}).get('position')}",
                "",
                "# Simulated Appearance (Preview-Only):",
            ]
            sim = p.get("simulated_features", {})
            for k, v in sim.items():
                lines.append(f"  {k}: {v}")

            self._current_preview = "\n".join(lines)
        else:
            self._current_preview = "No profile selected."

        self.previewChanged.emit()

    # Properties
    @Property("QVariantList", notify=profilesChanged)
    def profiles(self) -> List[Dict[str, Any]]:
        return self._filtered_profiles

    @Property("QVariantList", notify=profilesChanged)
    def allProfiles(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._all_profiles]

    @Property("QVariantMap", notify=selectedProfileChanged)
    def selectedProfile(self) -> Dict[str, Any]:
        if 0 <= self._selected_index < len(self._filtered_profiles):
            return self._filtered_profiles[self._selected_index]
        return self._filtered_profiles[0] if self._filtered_profiles else {}

    @Property(int, notify=selectedProfileChanged)
    def selectedIndex(self) -> int:
        return self._selected_index

    @Property(str, notify=selectedProfileChanged)
    def selectedProfileId(self) -> str:
        cur = self.selectedProfile
        return str(cur.get("id", ""))

    @Property("QVariantList", notify=categoryChanged)
    def categories(self) -> List[str]:
        return ["All", "Productivity", "Minimal", "Nothing-Inspired", "Imported"]

    @Property(str, notify=categoryChanged)
    def selectedCategory(self) -> str:
        return self._selected_category

    @Property(str, notify=searchQueryChanged)
    def searchQuery(self) -> str:
        return self._search_query

    @Property(int, notify=profilesChanged)
    def profileCount(self) -> int:
        return len(self._filtered_profiles)

    @Property(str, notify=previewChanged)
    def previewText(self) -> str:
        return self._current_preview

    # Backward compatibility aliases for Phase 1 tests
    @Property("QVariantList", notify=profilesChanged)
    def presets(self) -> List[Dict[str, Any]]:
        # Map profiles so they have title and preview_colors for Phase 1 legacy tests
        legacy_list = []
        for p in self._all_profiles:
            d = p.to_dict()
            d["title"] = p.name
            d["preview_colors"] = p.color_scheme.preview_colors
            legacy_list.append(d)
        return legacy_list

    @Property("QVariantMap", notify=selectedProfileChanged)
    def selectedPreset(self) -> Dict[str, Any]:
        cur = self.selectedProfile
        cur["title"] = cur.get("name", "")
        cur["preview_colors"] = cur.get("color_scheme", {}).get("preview_colors", {})
        return cur

    # Slots
    @Slot(int)
    def selectProfile(self, index: int) -> None:
        if 0 <= index < len(self._filtered_profiles) and index != self._selected_index:
            self._selected_index = index
            self.selectedProfileChanged.emit()
            self._update_preview()

    @Slot(int)
    def selectPreset(self, index: int) -> None:
        self.selectProfile(index)

    @Slot(str)
    def setCategory(self, cat: str) -> None:
        if self._selected_category != cat:
            self._selected_category = cat
            self._selected_index = 0
            self.categoryChanged.emit()
            self._apply_filter()

    @Slot(str)
    def setSearchQuery(self, query: str) -> None:
        if self._search_query != query:
            self._search_query = query
            self._selected_index = 0
            self.searchQueryChanged.emit()
            self._apply_filter()

    @Slot()
    def loadLayoutIntoDesktopBuilder(self) -> None:
        """Send the selected profile's layout model to Desktop Builder draft."""
        cur = self.selectedProfile
        layout_dict = cur.get("desktop_layout")
        if layout_dict:
            self.layoutTransferRequested.emit(layout_dict)
            self.profileOperationCompleted.emit(
                f"Loaded '{cur.get('name')}' layout into Desktop Builder draft.",
                True,
            )
        else:
            self.profileOperationCompleted.emit("Profile does not contain layout data.", False)

    @Slot()
    def applyColorSchemeViaThemeStudio(self) -> None:
        """Request Theme Studio to select and stage the profile's color scheme."""
        cur = self.selectedProfile
        cs = cur.get("color_scheme", {})
        scheme_id = cs.get("scheme_id", "")
        if scheme_id:
            self.themeTransferRequested.emit(scheme_id)
            self.profileOperationCompleted.emit(
                f"Selected '{cs.get('name', scheme_id)}' color scheme in Theme Studio.",
                True,
            )
        else:
            self.profileOperationCompleted.emit("Profile does not specify a color scheme.", False)

    @Slot(str, str, result=bool)
    def exportProfile(self, profile_id: str, dest_path: str = "") -> bool:
        """Export profile as JSON to the destination path."""
        pid = profile_id.strip() if profile_id.strip() else self.selectedProfileId
        if not pid:
            self.profileOperationCompleted.emit("No profile selected for export.", False)
            return False

        if not dest_path:
            # Default export location
            dest = Path.home() / f"{pid}_profile.json"
        else:
            dest = Path(dest_path)

        ok, msg = self._profile_manager.export_profile(pid, dest)
        self.profileOperationCompleted.emit(msg, ok)
        return ok

    @Slot(str, result=bool)
    def importProfileFile(self, file_path: str) -> bool:
        """Import a JSON profile file without applying it to KDE."""
        ok, msg, _ = self._profile_manager.import_profile_file(Path(file_path))
        self.profileOperationCompleted.emit(msg, ok)
        if ok:
            self.refresh()
            self.setCategory("Imported")
        return ok

    @Slot(str, result=bool)
    def importProfileJson(self, json_str: str) -> bool:
        """Import raw JSON string without applying it to KDE."""
        ok, msg, _ = self._profile_manager.import_profile_json(json_str)
        self.profileOperationCompleted.emit(msg, ok)
        if ok:
            self.refresh()
            self.setCategory("Imported")
        return ok

    @Slot(int, result=str)
    def inspectPresetDryRun(self, index: int) -> str:
        if 0 <= index < len(self._legacy_presets):
            preset = self._legacy_presets[index]
            changeset = preset.to_changeset()
            return self._dry_run_adapter.preview(changeset)
        return self._current_preview
