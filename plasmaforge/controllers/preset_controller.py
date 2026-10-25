"""Preset controller exposing Setup Gallery bundles and dry-run preview."""

from __future__ import annotations

from typing import Any, Dict, List

from PySide6.QtCore import Property, QObject, Signal, Slot

from plasmaforge.core.adapter_boundary import DryRunAdapter, SafetyViolationError
from plasmaforge.core.presets import get_all_presets


class PresetController(QObject):
    """Coordinates Setup Gallery presets and dry-run change inspections."""

    presetsChanged = Signal()
    selectedPresetChanged = Signal()
    previewChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._preset_models = get_all_presets()
        self._presets = [p.to_dict() for p in self._preset_models]
        self._selected_index = 0
        self._dry_run_adapter = DryRunAdapter(safe_mode=True)
        self._current_preview = ""
        self._update_preview()

    def _update_preview(self) -> None:
        if 0 <= self._selected_index < len(self._preset_models):
            preset = self._preset_models[self._selected_index]
            changeset = preset.to_changeset()
            self._current_preview = self._dry_run_adapter.preview(changeset)
        else:
            self._current_preview = "No preset selected."
        self.previewChanged.emit()

    @Property("QVariantList", notify=presetsChanged)
    def presets(self) -> List[Dict[str, Any]]:
        return self._presets

    @Property("QVariantMap", notify=selectedPresetChanged)
    def selectedPreset(self) -> Dict[str, Any]:
        if 0 <= self._selected_index < len(self._presets):
            return self._presets[self._selected_index]
        return {}

    @Property(int, notify=selectedPresetChanged)
    def selectedIndex(self) -> int:
        return self._selected_index

    @Property(str, notify=previewChanged)
    def previewText(self) -> str:
        return self._current_preview

    @Slot(int)
    def selectPreset(self, index: int) -> None:
        if 0 <= index < len(self._presets) and index != self._selected_index:
            self._selected_index = index
            self.selectedPresetChanged.emit()
            self._update_preview()

    @Slot(int, result=str)
    def inspectPresetDryRun(self, index: int) -> str:
        if 0 <= index < len(self._preset_models):
            preset = self._preset_models[index]
            changeset = preset.to_changeset()
            return self._dry_run_adapter.preview(changeset)
        return "Invalid preset index."
