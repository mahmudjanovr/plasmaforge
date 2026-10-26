"""Desktop controller coordinating live desktop inspection, editable draft workbench, presets, and safe transactional apply."""

from __future__ import annotations

import concurrent.futures
import datetime
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from plasmaforge.core.backup_manager import BackupManager
from plasmaforge.core.config import get_config, save_config
from plasmaforge.core.desktop_inspector import (
    DesktopChangeAnalyzer,
    DesktopEnvironmentDetector,
    DesktopLayoutInspector,
    LiveDesktopState,
    ProposedChange,
)
from plasmaforge.core.desktop_layout import (
    DesktopLayout,
    DesktopLayoutApplier,
    PanelConfig,
    detect_desktop_layout,
    get_layout_presets,
)
from plasmaforge.core.layout_presets import (
    LayoutPreset,
    LayoutPresetManager,
    get_curated_layout_presets,
)
from plasmaforge.core.transaction import TransactionResult, TransactionState
from plasmaforge.core.widget_catalog import InstalledWidgetInfo, WidgetCatalogService


class DesktopWorkerSignals(QObject):
    """Thread-safe signal dispatcher for desktop inspection worker."""

    inspectionCompleted = Signal(object)  # LiveDesktopState
    inspectionFailed = Signal(str)
    catalogCompleted = Signal(list, list)  # List[InstalledWidgetInfo], List[str]
    catalogFailed = Signal(str)


class DesktopController(QObject):
    """Exposes live desktop environment inspection, layout blueprints, interactive draft editing, and safe apply to QML."""

    layoutChanged = Signal()
    draftChanged = Signal()
    diffPreviewReady = Signal(str)
    confirmDialogVisibilityChanged = Signal(bool)
    applyFinished = Signal(bool, str, bool)  # success, message, is_dry_run
    restoreFinished = Signal(bool, str)

    # Live inspection signals
    inspectionStateChanged = Signal()
    environmentChanged = Signal()
    proposedChangesChanged = Signal()
    selectedPanelChanged = Signal()

    # Widget Catalog & Layout Presets signals
    widgetCatalogChanged = Signal()
    widgetCatalogLoadingChanged = Signal()
    customPresetsChanged = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        inspector: Optional[DesktopLayoutInspector] = None,
        detector: Optional[DesktopEnvironmentDetector] = None,
        applier: Optional[DesktopLayoutApplier] = None,
        catalog_service: Optional[WidgetCatalogService] = None,
        preset_manager: Optional[LayoutPresetManager] = None,
    ) -> None:
        super().__init__(parent)
        self._config = get_config()
        self._backup_manager = BackupManager()

        self._detector = detector or DesktopEnvironmentDetector()
        self._inspector = inspector or DesktopLayoutInspector(detector=self._detector)
        self._catalog_service = catalog_service or WidgetCatalogService()
        self._preset_manager = preset_manager or LayoutPresetManager()

        self._applier = applier or DesktopLayoutApplier(
            backup_manager=self._backup_manager,
            safe_mode=self._config.safe_mode,
        )

        self._presets = [p.to_dict() for p in self._preset_manager.list_presets()]
        self._selected_preset_id = ""

        # Widget Catalog state
        self._installed_widgets: List[InstalledWidgetInfo] = []
        self._widget_categories: List[str] = ["All"]
        self._is_catalog_loading = False

        # Live inspection state
        self._is_inspecting = False
        self._live_state: LiveDesktopState = self._inspector.inspect_desktop()
        self._last_inspection_time = self._format_timestamp(self._live_state.timestamp)

        # Sync detected blueprint from live state
        config_path = None
        if hasattr(self._applier, "source_config_dir") and self._applier.source_config_dir:
            config_path = self._applier.source_config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
        self._detected_layout: DesktopLayout = detect_desktop_layout(config_path=config_path)
        self._draft_layout: DesktopLayout = DesktopLayout.from_dict(self._detected_layout.to_dict())
        self._draft_layout.id = "custom_draft"
        self._draft_layout.name = "Custom Layout Draft"

        self._current_diff_preview = ""
        self._show_confirm_dialog = False
        self._is_applying = False
        self._last_backup_id = ""

        # Selected panel state for granular editing
        self._selected_panel_id = ""
        self._selected_panel_index = 0
        if self._live_state.panels:
            self._selected_panel_id = self._live_state.panels[0].containment_id or self._live_state.panels[0].id

        # Proposed changes list
        self._proposed_changes: List[Dict[str, Any]] = []
        self._recompute_proposed_changes()

        # Background threading
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="pf_desktop_",
        )
        self._signals = DesktopWorkerSignals(self)
        self._signals.inspectionCompleted.connect(self._on_inspection_completed)
        self._signals.inspectionFailed.connect(self._on_inspection_failed)
        self._signals.catalogCompleted.connect(self._on_catalog_completed)
        self._signals.catalogFailed.connect(self._on_catalog_failed)

        # Wire draft changes to update proposed changes
        self.draftChanged.connect(self._recompute_proposed_changes)

        # Kick off background widget catalog discovery
        self.loadWidgetCatalog()

    def _format_timestamp(self, iso_str: str) -> str:
        """Format ISO timestamp to readable local time string."""
        if not iso_str:
            return "Just now"
        try:
            dt = datetime.datetime.fromisoformat(iso_str)
            local_dt = dt.astimezone()
            return local_dt.strftime("%H:%M:%S")
        except Exception:
            return "Just now"

    # ==========================================
    # Live Inspection Slots & Properties
    # ==========================================
    @Slot()
    def refreshInspection(self) -> None:
        """Start asynchronous inspection of the live KDE Plasma desktop."""
        if self._is_inspecting:
            return

        self._is_inspecting = True
        self.inspectionStateChanged.emit()

        def worker() -> None:
            try:
                state = self._inspector.inspect_desktop()
                self._signals.inspectionCompleted.emit(state)
            except Exception as e:
                self._signals.inspectionFailed.emit(str(e))

        self._executor.submit(worker)

    @Slot()
    def refresh(self) -> None:
        """Re-detect active layout from KDE configuration files."""
        config_path = None
        if hasattr(self._applier, "source_config_dir") and self._applier.source_config_dir:
            config_path = self._applier.source_config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
        self._detected_layout = detect_desktop_layout(config_path=config_path)
        self._recompute_proposed_changes()
        self.layoutChanged.emit()

    def _on_inspection_completed(self, state: LiveDesktopState) -> None:
        """Handle inspection complete on the GUI thread."""
        self._live_state = state
        self._last_inspection_time = self._format_timestamp(state.timestamp)
        self._is_inspecting = False

        if not self._selected_panel_id and state.panels:
            self._selected_panel_id = state.panels[0].containment_id or state.panels[0].id
            self._selected_panel_index = 0
            self.selectedPanelChanged.emit()

        config_path = None
        if hasattr(self._applier, "source_config_dir") and self._applier.source_config_dir:
            config_path = self._applier.source_config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
        self._detected_layout = detect_desktop_layout(config_path=config_path)
        self._recompute_proposed_changes()

        self.inspectionStateChanged.emit()
        self.environmentChanged.emit()
        self.layoutChanged.emit()

    def _on_inspection_failed(self, err_msg: str) -> None:
        """Handle inspection failure."""
        self._is_inspecting = False
        self._live_state.status_message = f"Inspection error: {err_msg}"
        self.inspectionStateChanged.emit()

    # ==========================================
    # Widget Catalog Discovery
    # ==========================================
    @Slot()
    def loadWidgetCatalog(self) -> None:
        """Start asynchronous discovery of installed Plasma widgets."""
        if self._is_catalog_loading:
            return

        self._is_catalog_loading = True
        self.widgetCatalogLoadingChanged.emit()

        def worker() -> None:
            try:
                widgets = self._catalog_service.get_installed_widgets(force_refresh=True)
                categories = ["All"] + self._catalog_service.get_categories()
                self._signals.catalogCompleted.emit(widgets, categories)
            except Exception as e:
                self._signals.catalogFailed.emit(str(e))

        self._executor.submit(worker)

    def _on_catalog_completed(self, widgets: List[InstalledWidgetInfo], categories: List[str]) -> None:
        """Handle widget catalog completion on the GUI thread."""
        self._installed_widgets = widgets
        self._widget_categories = categories
        self._is_catalog_loading = False
        self.widgetCatalogLoadingChanged.emit()
        self.widgetCatalogChanged.emit()

    def _on_catalog_failed(self, err_msg: str) -> None:
        """Handle widget catalog scan error."""
        self._is_catalog_loading = False
        self.widgetCatalogLoadingChanged.emit()

    def _recompute_proposed_changes(self) -> None:
        """Compare detected layout with current workbench draft."""
        if not self.isDraftModified:
            self._proposed_changes = []
        else:
            changes = DesktopChangeAnalyzer.compare_states(
                self._detected_layout, self._draft_layout
            )
            self._proposed_changes = [c.to_dict() for c in changes]
        self.proposedChangesChanged.emit()

    @Property(bool, notify=inspectionStateChanged)
    def isInspecting(self) -> bool:
        return self._is_inspecting

    @Property(str, notify=inspectionStateChanged)
    def lastInspectionTime(self) -> str:
        return self._last_inspection_time

    @Property(str, notify=inspectionStateChanged)
    def inspectionSource(self) -> str:
        return self._live_state.inspection_source

    @Property(str, notify=inspectionStateChanged)
    def inspectionStatusText(self) -> str:
        return self._live_state.status_message

    @Property("QVariantMap", notify=environmentChanged)
    def environmentInfo(self) -> Dict[str, Any]:
        return {
            "plasma_version": self._live_state.plasma_version,
            "session_type": self._live_state.session_type,
            "distribution": self._live_state.distribution,
            "display_summary": self._live_state.display_summary,
            "displays": [d.to_dict() for d in self._live_state.displays],
            "active_look_and_feel": self._live_state.active_look_and_feel,
        }

    @Property("QVariantList", notify=inspectionStateChanged)
    def livePanels(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._live_state.panels]

    @Property("QVariantList", notify=inspectionStateChanged)
    def liveDesktopWidgets(self) -> List[Dict[str, Any]]:
        return [w.to_dict() for w in self._live_state.desktop_widgets]

    @Property(str, notify=inspectionStateChanged)
    def liveWallpaper(self) -> str:
        return self._live_state.wallpaper_image

    @Property("QVariantMap", notify=inspectionStateChanged)
    def inspectionCapabilities(self) -> Dict[str, bool]:
        return self._live_state.capabilities

    @Property("QVariantList", notify=inspectionStateChanged)
    def unsupportedFeatures(self) -> List[str]:
        return self._live_state.unsupported_features

    @Property("QVariantList", notify=proposedChangesChanged)
    def proposedChanges(self) -> List[Dict[str, Any]]:
        return self._proposed_changes

    # ==========================================
    # Legacy & Workbench Properties
    # ==========================================
    @Property("QVariantMap", notify=layoutChanged)
    def detectedLayout(self) -> Dict[str, Any]:
        return self._detected_layout.to_dict()

    @Property("QVariantMap", notify=draftChanged)
    def draftLayout(self) -> Dict[str, Any]:
        return self._draft_layout.to_dict()

    @Property("QVariantList", notify=layoutChanged)
    def presets(self) -> List[Dict[str, Any]]:
        return self._presets

    @Property(str, notify=draftChanged)
    def selectedPresetId(self) -> str:
        return self._selected_preset_id

    @Property(bool, notify=draftChanged)
    def isDraftModified(self) -> bool:
        """Returns True if draft settings differ from current detected layout."""
        d = self._draft_layout
        c = self._detected_layout
        return (
            d.top_panel.position != c.top_panel.position
            or d.top_panel.thickness != c.top_panel.thickness
            or d.top_panel.visibility != c.top_panel.visibility
            or d.top_panel.applets != c.top_panel.applets
            or d.dock.position != c.dock.position
            or d.dock.thickness != c.dock.thickness
            or d.dock.icon_size != c.dock.icon_size
            or d.dock.visibility != c.dock.visibility
            or d.dock.applets != c.dock.applets
            or d.desktop_widgets != c.desktop_widgets
            or d.show_widgets != c.show_widgets
        )

    # ------------------------------------------
    # Widget Catalog & Presets Properties
    # ------------------------------------------
    @Property(bool, notify=widgetCatalogLoadingChanged)
    def isCatalogLoading(self) -> bool:
        return self._is_catalog_loading

    @Property("QVariantList", notify=widgetCatalogChanged)
    def installedWidgets(self) -> List[Dict[str, Any]]:
        return [w.to_dict() for w in self._installed_widgets]

    @Property("QVariantList", notify=widgetCatalogChanged)
    def widgetCategories(self) -> List[str]:
        return self._widget_categories

    @Property("QVariantList", notify=customPresetsChanged)
    def customPresets(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._preset_manager.list_presets() if not p.is_builtin]

    @Property("QVariantList", notify=draftChanged)
    def selectedPanelApplets(self) -> List[str]:
        cfg = self._get_selected_draft_config()
        return list(cfg.applets) if cfg else []

    @Property("QVariantList", notify=draftChanged)
    def desktopWidgets(self) -> List[str]:
        return list(self._draft_layout.desktop_widgets)

    @Property(bool, notify=proposedChangesChanged)
    def hasProposedChanges(self) -> bool:
        return len(self._proposed_changes) > 0

    @Property(str, notify=diffPreviewReady)
    def currentDiffPreview(self) -> str:
        return self._current_diff_preview

    @Property(bool, notify=confirmDialogVisibilityChanged)
    def showConfirmDialog(self) -> bool:
        return self._show_confirm_dialog

    @Property(bool, notify=applyFinished)
    def isApplying(self) -> bool:
        return self._is_applying

    @Property(bool, notify=restoreFinished)
    def canRestorePrevious(self) -> bool:
        return bool(self._last_backup_id)

    @Property(str, notify=restoreFinished)
    def lastBackupId(self) -> str:
        return self._last_backup_id

    # ------------------------------------------
    # Multi-Panel Selection & Editing
    # ------------------------------------------
    def _get_selected_live_panel(self) -> Optional[DetectedPanelInfo]:
        if not self._live_state.panels:
            return None
        if self._selected_panel_id:
            for p in self._live_state.panels:
                if p.containment_id == self._selected_panel_id or p.id == self._selected_panel_id:
                    return p
        if 0 <= self._selected_panel_index < len(self._live_state.panels):
            return self._live_state.panels[self._selected_panel_index]
        return self._live_state.panels[0]

    def _get_selected_draft_config(self) -> Optional[PanelConfig]:
        live_p = self._get_selected_live_panel()
        if not live_p:
            return self._draft_layout.top_panel

        cid = live_p.containment_id
        if cid and self._draft_layout.top_panel.containment_id == cid:
            return self._draft_layout.top_panel
        if cid and self._draft_layout.dock.containment_id == cid:
            return self._draft_layout.dock

        if live_p.position == "top" or (not live_p.is_dock and live_p.position != "bottom"):
            if not self._draft_layout.top_panel.containment_id and cid:
                self._draft_layout.top_panel.containment_id = cid
            return self._draft_layout.top_panel
        else:
            if not self._draft_layout.dock.containment_id and cid:
                self._draft_layout.dock.containment_id = cid
            return self._draft_layout.dock

    @Property(str, notify=selectedPanelChanged)
    def selectedPanelId(self) -> str:
        return self._selected_panel_id

    @Property(int, notify=selectedPanelChanged)
    def selectedPanelIndex(self) -> int:
        return self._selected_panel_index

    @Property("QVariantMap", notify=selectedPanelChanged)
    def selectedPanelInfo(self) -> Dict[str, Any]:
        p = self._get_selected_live_panel()
        if p:
            return p.to_dict()
        return {}

    @Property(str, notify=draftChanged)
    def selectedPanelPosition(self) -> str:
        cfg = self._get_selected_draft_config()
        return cfg.position if cfg else "top"

    @Property(int, notify=draftChanged)
    def selectedPanelThickness(self) -> int:
        cfg = self._get_selected_draft_config()
        return cfg.thickness if cfg else 36

    @Property(str, notify=draftChanged)
    def selectedPanelVisibility(self) -> str:
        cfg = self._get_selected_draft_config()
        return cfg.visibility if cfg else "always_visible"

    @Property(bool, notify=inspectionStateChanged)
    def isLiveEditingSupported(self) -> bool:
        return self._applier.live_editor.is_live_dbus_supported()

    @Property(bool, notify=selectedPanelChanged)
    def selectedPanelIsLiveSupported(self) -> bool:
        p = self._get_selected_live_panel()
        if not p or not p.containment_id:
            return False
        return self._applier.live_editor.is_live_dbus_supported()

    @Property(bool, notify=draftChanged)
    def selectedPanelHasChanges(self) -> bool:
        live_p = self._get_selected_live_panel()
        draft_cfg = self._get_selected_draft_config()
        if not live_p or not draft_cfg:
            return False
        return (
            live_p.position != draft_cfg.position
            or abs(live_p.thickness - draft_cfg.thickness) >= 2
            or live_p.visibility != draft_cfg.visibility
        )

    @Slot(str)
    def selectPanel(self, panel_id: str) -> None:
        """Select a detected panel containment for editing."""
        if self._selected_panel_id != panel_id:
            self._selected_panel_id = panel_id
            for idx, p in enumerate(self._live_state.panels):
                if p.containment_id == panel_id or p.id == panel_id:
                    self._selected_panel_index = idx
                    break
            self.selectedPanelChanged.emit()

    @Slot(int)
    def selectPanelByIndex(self, index: int) -> None:
        if 0 <= index < len(self._live_state.panels):
            p = self._live_state.panels[index]
            self._selected_panel_index = index
            self._selected_panel_id = p.containment_id or p.id
            self.selectedPanelChanged.emit()

    @Slot(str)
    def setSelectedPanelPosition(self, pos: str) -> None:
        cfg = self._get_selected_draft_config()
        if cfg and cfg.position != pos:
            cfg.position = pos
            self._selected_preset_id = "custom"
            self.draftChanged.emit()

    @Slot(int)
    def setSelectedPanelThickness(self, val: int) -> None:
        clamped = max(16, min(128, val))
        cfg = self._get_selected_draft_config()
        if cfg and cfg.thickness != clamped:
            cfg.thickness = clamped
            self._selected_preset_id = "custom"
            self.draftChanged.emit()

    @Slot(str)
    def setSelectedPanelVisibility(self, vis: str) -> None:
        cfg = self._get_selected_draft_config()
        if cfg and cfg.visibility != vis:
            cfg.visibility = vis
            self._selected_preset_id = "custom"
            self.draftChanged.emit()

    # Granular bindings for QML sliders/radios
    @Property(str, notify=draftChanged)
    def panelPosition(self) -> str:
        return self._draft_layout.top_panel.position

    @Property(int, notify=draftChanged)
    def panelThickness(self) -> int:
        return self._draft_layout.top_panel.thickness

    @Property(str, notify=draftChanged)
    def panelVisibility(self) -> str:
        return self._draft_layout.top_panel.visibility

    @Property(str, notify=draftChanged)
    def dockPosition(self) -> str:
        return self._draft_layout.dock.position

    @Property(int, notify=draftChanged)
    def dockThickness(self) -> int:
        return self._draft_layout.dock.thickness

    @Property(int, notify=draftChanged)
    def dockIconSize(self) -> int:
        return self._draft_layout.dock.icon_size

    @Property(str, notify=draftChanged)
    def dockVisibility(self) -> str:
        return self._draft_layout.dock.visibility

    @Property(bool, notify=draftChanged)
    def showWidgets(self) -> bool:
        return self._draft_layout.show_widgets

    # Setters
    @Slot(str)
    def setPanelPosition(self, pos: str) -> None:
        if self._draft_layout.top_panel.position != pos:
            self._draft_layout.top_panel.position = pos
            self._selected_preset_id = "custom"
            self.draftChanged.emit()

    @Slot(int)
    def setPanelThickness(self, val: int) -> None:
        clamped = max(16, min(128, val))
        if self._draft_layout.top_panel.thickness != clamped:
            self._draft_layout.top_panel.thickness = clamped
            self._selected_preset_id = "custom"
            self.draftChanged.emit()

    @Slot(str)
    def setPanelVisibility(self, vis: str) -> None:
        if self._draft_layout.top_panel.visibility != vis:
            self._draft_layout.top_panel.visibility = vis
            self._selected_preset_id = "custom"
            self.draftChanged.emit()

    @Slot(str)
    def setDockPosition(self, pos: str) -> None:
        if self._draft_layout.dock.position != pos:
            self._draft_layout.dock.position = pos
            self._selected_preset_id = "custom"
            self.draftChanged.emit()

    @Slot(int)
    def setDockThickness(self, val: int) -> None:
        clamped = max(24, min(128, val))
        if self._draft_layout.dock.thickness != clamped:
            self._draft_layout.dock.thickness = clamped
            self._selected_preset_id = "custom"
            self.draftChanged.emit()

    @Slot(int)
    def setDockIconSize(self, val: int) -> None:
        clamped = max(16, min(96, val))
        if self._draft_layout.dock.icon_size != clamped:
            self._draft_layout.dock.icon_size = clamped
            self._selected_preset_id = "custom"
            self.draftChanged.emit()

    @Slot(str)
    def setDockVisibility(self, vis: str) -> None:
        if self._draft_layout.dock.visibility != vis:
            self._draft_layout.dock.visibility = vis
            self._selected_preset_id = "custom"
            self.draftChanged.emit()

    @Slot(bool)
    def setShowWidgets(self, val: bool) -> None:
        if self._draft_layout.show_widgets != val:
            self._draft_layout.show_widgets = val
            self._selected_preset_id = "custom"
            self.draftChanged.emit()

    @Slot(str)
    def loadPreset(self, preset_id: str) -> None:
        """Load a curated or custom preset into the editable draft workbench."""
        preset = self._preset_manager.get_preset(preset_id)
        if preset:
            top_cid = self._detected_layout.top_panel.containment_id
            dock_cid = self._detected_layout.dock.containment_id

            self._draft_layout = preset.to_desktop_layout()
            self._draft_layout.top_panel.containment_id = top_cid
            self._draft_layout.dock.containment_id = dock_cid
            self._selected_preset_id = preset_id
            self.draftChanged.emit()

    # ------------------------------------------
    # Widget Placement & Management Slots
    # ------------------------------------------
    @Slot(str, str, str, result="QVariantList")
    def searchWidgets(self, query: str = "", category: str = "", target: str = "") -> List[Dict[str, Any]]:
        """Filter discovered widgets by query string, category, and target ('panel' or 'desktop')."""
        results = self._catalog_service.search_widgets(
            query=query,
            category=category,
            target=target,
            widgets=self._installed_widgets if self._installed_widgets else None,
        )
        return [w.to_dict() for w in results]

    def _resolve_draft_panel(self, containment_id: str = "") -> Optional[PanelConfig]:
        """Resolve target draft panel config by ID or fall back to selected panel."""
        if containment_id:
            if containment_id in ("dock", "bottom") or containment_id == self._draft_layout.dock.containment_id:
                return self._draft_layout.dock
            if containment_id in ("top", "panel") or containment_id == self._draft_layout.top_panel.containment_id:
                return self._draft_layout.top_panel
            if self._draft_layout.top_panel.containment_id == containment_id:
                return self._draft_layout.top_panel
            if self._draft_layout.dock.containment_id == containment_id:
                return self._draft_layout.dock
        return self._get_selected_draft_config()

    @Slot(str, str, result=bool)
    def addAppletToDraft(self, containment_id: str, plugin_id: str) -> bool:
        """Stage an applet addition into the specified or selected panel draft."""
        if not plugin_id:
            return False
        panel = self._resolve_draft_panel(containment_id)
        if panel is not None:
            panel.applets.append(plugin_id)
            self._selected_preset_id = "custom"
            self.draftChanged.emit()
            return True
        return False

    @Slot(str, int, result=bool)
    def removeAppletFromDraft(self, containment_id: str, applet_index: int) -> bool:
        """Stage an applet removal from the specified or selected panel draft."""
        panel = self._resolve_draft_panel(containment_id)
        if panel is not None and 0 <= applet_index < len(panel.applets):
            panel.applets.pop(applet_index)
            self._selected_preset_id = "custom"
            self.draftChanged.emit()
            return True
        return False

    @Slot(str, int, int, result=bool)
    def moveAppletInDraft(self, containment_id: str, from_index: int, to_index: int) -> bool:
        """Reorder applet in specified or selected panel draft."""
        panel = self._resolve_draft_panel(containment_id)
        if panel is not None and 0 <= from_index < len(panel.applets) and 0 <= to_index < len(panel.applets):
            item = panel.applets.pop(from_index)
            panel.applets.insert(to_index, item)
            self._selected_preset_id = "custom"
            self.draftChanged.emit()
            return True
        return False

    @Slot(str, result=bool)
    def addDesktopWidgetToDraft(self, plugin_id: str) -> bool:
        """Stage a widget addition to desktop containments."""
        if not plugin_id:
            return False
        self._draft_layout.desktop_widgets.append(plugin_id)
        self._draft_layout.show_widgets = True
        self._selected_preset_id = "custom"
        self.draftChanged.emit()
        return True

    @Slot(int, result=bool)
    def removeDesktopWidgetFromDraft(self, widget_index: int) -> bool:
        """Stage a widget removal from desktop containments."""
        if 0 <= widget_index < len(self._draft_layout.desktop_widgets):
            self._draft_layout.desktop_widgets.pop(widget_index)
            self._selected_preset_id = "custom"
            self.draftChanged.emit()
            return True
        return False

    # ------------------------------------------
    # Custom Layout Presets Slots
    # ------------------------------------------
    @Slot(str, str, str, result=bool)
    def saveDraftAsPreset(self, preset_id: str, name: str, description: str) -> bool:
        """Save current draft layout as a custom preset."""
        cleaned_id = preset_id.strip() or re.sub(r"[^a-z0-9_]+", "_", name.lower().strip())
        cleaned_id = re.sub(r"[^a-z0-9_-]", "_", cleaned_id.lower()).strip("_")
        if not cleaned_id:
            cleaned_id = f"custom_preset_{int(datetime.datetime.now().timestamp())}"

        preset = LayoutPreset.from_desktop_layout(
            layout=self._draft_layout,
            preset_id=cleaned_id,
            name=name.strip() or "Custom Layout Preset",
            description=description.strip() or "User saved desktop layout preset.",
            author="User",
        )
        ok, msg = self._preset_manager.save_preset(preset, overwrite=True)
        if ok:
            self._presets = [p.to_dict() for p in self._preset_manager.list_presets()]
            self._selected_preset_id = cleaned_id
            self.customPresetsChanged.emit()
            self.layoutChanged.emit()
            return True
        return False

    @Slot(str, result=bool)
    def deleteCustomPreset(self, preset_id: str) -> bool:
        """Delete a saved custom layout preset."""
        ok, msg = self._preset_manager.delete_preset(preset_id)
        if ok:
            self._presets = [p.to_dict() for p in self._preset_manager.list_presets()]
            if self._selected_preset_id == preset_id:
                self._selected_preset_id = ""
            self.customPresetsChanged.emit()
            self.layoutChanged.emit()
            return True
        return False

    @Slot(str, result="QVariantList")
    def checkPresetMissingWidgets(self, preset_id: str) -> List[str]:
        """Check for missing widgets required by a preset."""
        return self._preset_manager.check_missing_widgets(preset_id, self._catalog_service)

    @Slot("QVariantMap")
    def loadDraftFromDict(self, layout_dict: Dict[str, Any]) -> None:
        """Load a desktop layout dictionary into the editable draft workbench."""
        top_cid = self._detected_layout.top_panel.containment_id
        dock_cid = self._detected_layout.dock.containment_id

        self._draft_layout = DesktopLayout.from_dict(layout_dict)
        if top_cid and not self._draft_layout.top_panel.containment_id:
            self._draft_layout.top_panel.containment_id = top_cid
        if dock_cid and not self._draft_layout.dock.containment_id:
            self._draft_layout.dock.containment_id = dock_cid

        self._selected_preset_id = self._draft_layout.id
        self.draftChanged.emit()

    @Slot()
    def resetDraft(self) -> None:
        """Reset draft back to the current detected layout."""
        self._draft_layout = DesktopLayout.from_dict(self._detected_layout.to_dict())
        self._draft_layout.id = "custom_draft"
        self._draft_layout.name = "Custom Layout Draft"
        self._selected_preset_id = ""
        self.draftChanged.emit()

    @Slot()
    def requestDiffPreview(self) -> None:
        """Compute unified diff for proposed layout against live config."""
        diff = self._applier.generate_diff_preview(self._draft_layout)
        self._current_diff_preview = diff
        self.diffPreviewReady.emit(diff)

    @Slot()
    def requestApplyDraft(self) -> None:
        """Open the layout apply confirmation dialog."""
        self._current_diff_preview = self._applier.generate_diff_preview(self._draft_layout)
        self._show_confirm_dialog = True
        self.confirmDialogVisibilityChanged.emit(True)
        self.diffPreviewReady.emit(self._current_diff_preview)

    @Slot()
    def cancelApply(self) -> None:
        self._show_confirm_dialog = False
        self.confirmDialogVisibilityChanged.emit(False)

    @Slot()
    def confirmApplyDraft(self) -> None:
        """Execute transactional apply of layout draft."""
        self._show_confirm_dialog = False
        self.confirmDialogVisibilityChanged.emit(False)

        self._is_applying = True
        config = get_config()
        self._applier.safe_mode = config.safe_mode

        res: TransactionResult = self._applier.apply_layout(self._draft_layout)
        self._is_applying = False

        if res.success and not res.is_dry_run:
            self._last_backup_id = res.backup_id
            self.restoreFinished.emit(True, "Layout applied and verified on disk.")
            self.refreshInspection()

        self.applyFinished.emit(res.success, res.message, res.is_dry_run)

    @Slot()
    def restorePreviousLayout(self) -> None:
        """Restore configuration from the pre-apply layout backup."""
        if not self._last_backup_id:
            self.restoreFinished.emit(False, "No pre-apply layout backup recorded to restore.")
            return

        res = self._applier.safety_engine.restore_snapshot_transactionally(
            snap_id=self._last_backup_id,
            file_whitelist=["plasma-org.kde.plasma.desktop-appletsrc"],
            confirmed=True,
            force_safe_mode=False,
        )

        if res.success:
            # Revert live D-Bus panel properties if live D-Bus is supported and safe mode is not forced
            if not get_config().safe_mode and self._applier.live_editor.is_live_dbus_supported():
                try:
                    config_file = self._applier.source_config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
                    restored_layout = detect_desktop_layout(config_file)
                    for p in [restored_layout.top_panel, restored_layout.dock]:
                        if p.containment_id and p.position != "none":
                            self._applier.live_editor.apply_panel_properties(
                                containment_id=p.containment_id,
                                location=p.position,
                                height=p.thickness,
                                visibility=p.visibility,
                            )
                except Exception:
                    pass

            self._last_backup_id = ""
            self.refreshInspection()
            self.resetDraft()

        self.restoreFinished.emit(res.success, res.message)
