"""Theme controller exposing discovered color schemes and plasma styles."""

from __future__ import annotations

from typing import Any, Dict, List

from PySide6.QtCore import Property, QObject, Signal, Slot

from plasmaforge.core.themes import ThemeInspector


class ThemeController(QObject):
    """Coordinates color schemes and plasma desktop theme inspection."""

    schemesChanged = Signal()
    stylesChanged = Signal()
    selectedSchemeChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._inspector = ThemeInspector()
        self._schemes: List[Dict[str, Any]] = []
        self._styles: List[Dict[str, Any]] = []
        self._selected_scheme_index = 0
        self.refresh()

    @Slot()
    def refresh(self) -> None:
        self._schemes = [s.to_dict() for s in self._inspector.get_color_schemes()]
        self._styles = [st.to_dict() for st in self._inspector.get_plasma_styles()]
        if not self._schemes:
            # Fallback mock for offline/non-KDE host test environments
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
                }
            ]
        self.schemesChanged.emit()
        self.stylesChanged.emit()
        self.selectedSchemeChanged.emit()

    @Property("QVariantList", notify=schemesChanged)
    def colorSchemes(self) -> List[Dict[str, Any]]:
        return self._schemes

    @Property("QVariantList", notify=stylesChanged)
    def plasmaStyles(self) -> List[Dict[str, Any]]:
        return self._styles

    @Property("QVariantMap", notify=selectedSchemeChanged)
    def selectedScheme(self) -> Dict[str, Any]:
        if 0 <= self._selected_scheme_index < len(self._schemes):
            return self._schemes[self._selected_scheme_index]
        return self._schemes[0] if self._schemes else {}

    @Property(int, notify=selectedSchemeChanged)
    def selectedSchemeIndex(self) -> int:
        return self._selected_scheme_index

    @Slot(int)
    def selectScheme(self, index: int) -> None:
        if 0 <= index < len(self._schemes):
            self._selected_scheme_index = index
            self.selectedSchemeChanged.emit()
