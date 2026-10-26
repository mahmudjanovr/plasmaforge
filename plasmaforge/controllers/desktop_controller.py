"""Desktop controller coordinating live desktop inspection, editable draft workbench, presets, and safe transactional apply."""

from __future__ import annotations

import concurrent.futures
import datetime
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
    detect_desktop_layout,
    get_layout_presets,
)
from plasmaforge.core.transaction import TransactionResult, TransactionState


class DesktopWorkerSignals(QObject):
    """Thread-safe signal dispatcher for desktop inspection worker."""

    inspectionCompleted = Signal(object)  # LiveDesktopState
    inspectionFailed = Signal(str)


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

    def __init__(
        self,
        parent: QObject | None = None,
        inspector: Optional[DesktopLayoutInspector] = None,
        detector: Optional[DesktopEnvironmentDetector] = None,
        applier: Optional[DesktopLayoutApplier] = None,
    ) -> None:
        super().__init__(parent)
        self._config = get_config()
        self._backup_manager = BackupManager()

        self._detector = detector or DesktopEnvironmentDetector()
        self._inspector = inspector or DesktopLayoutInspector(detector=self._detector)
        self._applier = applier or DesktopLayoutApplier(
            backup_manager=self._backup_manager,
            safe_mode=self._config.safe_mode,
        )

        self._presets = [p.to_dict() for p in get_layout_presets()]
        self._selected_preset_id = ""

        # Live inspection state
        self._is_inspecting = False
        self._live_state: LiveDesktopState = self._inspector.inspect_desktop()
        self._last_inspection_time = self._format_timestamp(self._live_state.timestamp)

        # Sync detected blueprint from live state
        self._detected_layout: DesktopLayout = detect_desktop_layout()
        self._draft_layout: DesktopLayout = DesktopLayout.from_dict(self._detected_layout.to_dict())
        self._draft_layout.id = "custom_draft"
        self._draft_layout.name = "Custom Layout Draft"

        self._current_diff_preview = ""
        self._show_confirm_dialog = False
        self._is_applying = False
        self._last_backup_id = ""

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

        # Wire draft changes to update proposed changes
        self.draftChanged.connect(self._recompute_proposed_changes)

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

        self._detected_layout = detect_desktop_layout()
        self._recompute_proposed_changes()

        self.inspectionStateChanged.emit()
        self.environmentChanged.emit()
        self.layoutChanged.emit()

    def _on_inspection_failed(self, err_msg: str) -> None:
        """Handle inspection failure."""
        self._is_inspecting = False
        self._live_state.status_message = f"Inspection error: {err_msg}"
        self.inspectionStateChanged.emit()

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
            or d.dock.position != c.dock.position
            or d.dock.thickness != c.dock.thickness
            or d.dock.icon_size != c.dock.icon_size
            or d.dock.visibility != c.dock.visibility
            or d.show_widgets != c.show_widgets
        )

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
        """Load a curated preset into the editable draft workbench."""
        for p in get_layout_presets():
            if p.id == preset_id:
                top_cid = self._detected_layout.top_panel.containment_id
                dock_cid = self._detected_layout.dock.containment_id

                self._draft_layout = DesktopLayout.from_dict(p.to_dict())
                self._draft_layout.top_panel.containment_id = top_cid
                self._draft_layout.dock.containment_id = dock_cid
                self._selected_preset_id = preset_id
                self.draftChanged.emit()
                break

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
            self._last_backup_id = ""
            self.refreshInspection()
            self.resetDraft()

        self.restoreFinished.emit(res.success, res.message)
