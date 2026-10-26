"""Reusable layout preset model and manager for PlasmaForge Desktop Builder.

Supports versioned JSON serialization, atomic file operations, validation,
and widget dependency verification for desktop layout presets.
"""

from __future__ import annotations

import datetime
import json
import logging
import re
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from plasmaforge.core.desktop_layout import DesktopLayout, PanelConfig

logger = logging.getLogger(__name__)

PRESET_SCHEMA_VERSION = 1


@dataclass
class LayoutPreset:
    """Versioned desktop layout preset specification."""

    id: str
    name: str
    description: str
    author: str = "User"
    created_at: str = ""
    schema_version: int = PRESET_SCHEMA_VERSION
    top_panel: PanelConfig = field(default_factory=lambda: PanelConfig(position="top", thickness=32))
    dock: PanelConfig = field(default_factory=lambda: PanelConfig(position="bottom", thickness=48, is_dock=True))
    desktop_widgets: List[str] = field(default_factory=list)
    show_widgets: bool = False
    required_widgets: List[str] = field(default_factory=list)
    compatibility_warnings: List[str] = field(default_factory=list)
    is_builtin: bool = False

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.datetime.now().astimezone().isoformat()
        # Collect required widgets automatically if not provided
        if not self.required_widgets:
            reqs: Set[str] = set()
            for applet in self.top_panel.applets:
                clean = self._normalize_plugin_id(applet)
                if clean:
                    reqs.add(clean)
            for applet in self.dock.applets:
                clean = self._normalize_plugin_id(applet)
                if clean:
                    reqs.add(clean)
            for widget in self.desktop_widgets:
                clean = self._normalize_plugin_id(widget)
                if clean:
                    reqs.add(clean)
            self.required_widgets = sorted(reqs)

    @staticmethod
    def _normalize_plugin_id(name: str) -> str:
        name = name.strip()
        if not name:
            return ""
        if not name.startswith("org.kde.") and not name.startswith("com."):
            return f"org.kde.plasma.{name}"
        return name

    def validate(self) -> List[str]:
        """Validate preset schema, bounds, and parameters."""
        errors: List[str] = []
        if not self.id or not re.match(r"^[a-zA-Z0-9_\-]+$", self.id):
            errors.append(f"Invalid preset ID '{self.id}'. Only alphanumeric characters, dashes, and underscores allowed.")
        if not self.name.strip():
            errors.append("Preset name cannot be empty.")
        if self.schema_version != PRESET_SCHEMA_VERSION:
            errors.append(f"Unsupported schema version {self.schema_version}. Expected {PRESET_SCHEMA_VERSION}.")

        errors.extend([f"Top panel: {e}" for e in self.top_panel.validate()])
        errors.extend([f"Dock: {e}" for e in self.dock.validate()])
        return errors

    def to_desktop_layout(self) -> DesktopLayout:
        """Convert preset into an editable workbench draft DesktopLayout."""
        return DesktopLayout(
            id=self.id,
            name=self.name,
            description=self.description,
            top_panel=PanelConfig.from_dict(self.top_panel.to_dict()),
            dock=PanelConfig.from_dict(self.dock.to_dict()),
            desktop_widgets=list(self.desktop_widgets),
            show_widgets=self.show_widgets or len(self.desktop_widgets) > 0,
            is_detected=False,
            is_preset=True,
        )

    @classmethod
    def from_desktop_layout(
        cls,
        layout: DesktopLayout,
        preset_id: str,
        name: str,
        description: str = "",
        author: str = "User",
    ) -> LayoutPreset:
        """Create a LayoutPreset from a DesktopLayout instance."""
        req_widgets = list(layout.top_panel.applets) + list(layout.dock.applets)
        return cls(
            schema_version=PRESET_SCHEMA_VERSION,
            id=preset_id,
            name=name,
            description=description,
            author=author,
            top_panel=PanelConfig.from_dict(layout.top_panel.to_dict()),
            dock=PanelConfig.from_dict(layout.dock.to_dict()),
            desktop_widgets=list(layout.desktop_widgets),
            show_widgets=layout.show_widgets or len(layout.desktop_widgets) > 0,
            required_widgets=sorted(list(set(req_widgets))),
            is_builtin=False,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "created_at": self.created_at,
            "top_panel": self.top_panel.to_dict(),
            "dock": self.dock.to_dict(),
            "desktop_widgets": list(self.desktop_widgets),
            "show_widgets": self.show_widgets,
            "required_widgets": list(self.required_widgets),
            "compatibility_warnings": list(self.compatibility_warnings),
            "is_builtin": self.is_builtin,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LayoutPreset:
        return cls(
            schema_version=int(data.get("schema_version", PRESET_SCHEMA_VERSION)),
            id=str(data.get("id", "custom")),
            name=str(data.get("name", "Custom Preset")),
            description=str(data.get("description", "")),
            author=str(data.get("author", "User")),
            created_at=str(data.get("created_at", "")),
            top_panel=PanelConfig.from_dict(data.get("top_panel", {})),
            dock=PanelConfig.from_dict(data.get("dock", {})),
            desktop_widgets=[str(w) for w in data.get("desktop_widgets", [])],
            show_widgets=bool(data.get("show_widgets", False)),
            required_widgets=[str(r) for r in data.get("required_widgets", [])],
            compatibility_warnings=[str(c) for c in data.get("compatibility_warnings", [])],
            is_builtin=bool(data.get("is_builtin", False)),
        )


def get_curated_layout_presets() -> List[LayoutPreset]:
    """Curated built-in layout presets."""
    return [
        LayoutPreset(
            id="classic_kde",
            name="Classic KDE",
            description="Conventional full-width bottom panel containing app launcher, task manager, and system tray.",
            author="KDE Community",
            top_panel=PanelConfig(
                position="none",
                thickness=32,
                visibility="always_visible",
                applets=[],
            ),
            dock=PanelConfig(
                position="bottom",
                thickness=44,
                visibility="always_visible",
                is_dock=False,
                icon_size=36,
                applets=["org.kde.plasma.kickoff", "org.kde.plasma.taskmanager", "org.kde.plasma.systemtray", "org.kde.plasma.digitalclock"],
            ),
            show_widgets=False,
            required_widgets=["org.kde.plasma.kickoff", "org.kde.plasma.taskmanager", "org.kde.plasma.systemtray", "org.kde.plasma.digitalclock"],
            compatibility_warnings=[],
            is_builtin=True,
        ),
        LayoutPreset(
            id="nothing_inspired",
            name="Nothing-Inspired",
            description="Minimalist dual arrangement: sleek top status bar and centered floating bottom dock with Nothing widgets.",
            author="PlasmaForge",
            top_panel=PanelConfig(
                position="top",
                thickness=32,
                visibility="always_visible",
                applets=["org.kde.plasma.kickoff", "org.kde.plasma.appmenu", "org.kde.plasma.digitalclock", "org.kde.plasma.systemtray"],
            ),
            dock=PanelConfig(
                position="bottom",
                thickness=52,
                visibility="dodge_windows",
                is_dock=True,
                icon_size=44,
                applets=["org.kde.plasma.icontasks"],
            ),
            desktop_widgets=["com.github.prayag2.modernclock"],
            show_widgets=True,
            required_widgets=["org.kde.plasma.kickoff", "org.kde.plasma.digitalclock", "org.kde.plasma.systemtray", "org.kde.plasma.icontasks"],
            compatibility_warnings=["Freeform desktop widget placement coordinates are simulated in builder preview."],
            is_builtin=True,
        ),
        LayoutPreset(
            id="clean_minimal",
            name="Clean Minimal",
            description="Distraction-free auto-hiding layout maximizing active workspace real estate.",
            author="PlasmaForge",
            top_panel=PanelConfig(
                position="top",
                thickness=30,
                visibility="auto_hide",
                applets=["org.kde.plasma.systemtray", "org.kde.plasma.digitalclock"],
            ),
            dock=PanelConfig(
                position="bottom",
                thickness=46,
                visibility="auto_hide",
                is_dock=True,
                icon_size=38,
                applets=["org.kde.plasma.icontasks"],
            ),
            show_widgets=False,
            required_widgets=["org.kde.plasma.systemtray", "org.kde.plasma.digitalclock", "org.kde.plasma.icontasks"],
            compatibility_warnings=[],
            is_builtin=True,
        ),
        LayoutPreset(
            id="dual_status_dock",
            name="Dual Status & Dock",
            description="Full-width top panel with system telemetry and launchers; floating bottom app launcher dock.",
            author="PlasmaForge",
            top_panel=PanelConfig(
                position="top",
                thickness=34,
                visibility="always_visible",
                applets=["org.kde.plasma.kickoff", "org.kde.plasma.panelspacer", "org.kde.plasma.digitalclock", "org.kde.plasma.panelspacer", "org.kde.plasma.systemmonitor", "org.kde.plasma.systemtray"],
            ),
            dock=PanelConfig(
                position="bottom",
                thickness=54,
                visibility="dodge_windows",
                is_dock=True,
                icon_size=44,
                applets=["org.kde.plasma.icontasks", "org.kde.plasma.mediacontroller", "org.kde.plasma.trash"],
            ),
            show_widgets=False,
            required_widgets=["org.kde.plasma.kickoff", "org.kde.plasma.digitalclock", "org.kde.plasma.systemtray", "org.kde.plasma.icontasks"],
            compatibility_warnings=[],
            is_builtin=True,
        ),
    ]


class LayoutPresetManager:
    """Manages saving, loading, importing, exporting, and validation of desktop layout presets."""

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self.storage_dir = storage_dir or (Path.home() / ".local" / "share" / "plasmaforge" / "layout_presets")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def list_presets(self) -> List[LayoutPreset]:
        """List all available presets (built-in curated presets + user saved presets)."""
        presets: Dict[str, LayoutPreset] = {}

        # 1. Built-in presets
        for p in get_curated_layout_presets():
            presets[p.id] = p

        # 2. User presets from storage directory
        if self.storage_dir.is_dir():
            for file_path in self.storage_dir.glob("*.json"):
                if file_path.is_file():
                    try:
                        data = json.loads(file_path.read_text(encoding="utf-8"))
                        preset = LayoutPreset.from_dict(data)
                        preset.is_builtin = False
                        presets[preset.id] = preset
                    except Exception as e:
                        logger.warning("Failed to load preset from %s: %s", file_path, e)

        return list(presets.values())

    def get_preset(self, preset_id: str) -> Optional[LayoutPreset]:
        """Retrieve a preset by ID."""
        for p in self.list_presets():
            if p.id == preset_id:
                return p
        return None

    def save_preset(self, preset: LayoutPreset, overwrite: bool = False) -> Tuple[bool, str]:
        """Save a layout preset atomically to the user presets directory."""
        errors = preset.validate()
        if errors:
            return False, f"Preset validation failed: {'; '.join(errors)}"

        if preset.is_builtin:
            return False, "Cannot overwrite built-in layout presets."

        target_file = self.storage_dir / f"{preset.id}.json"
        if target_file.exists() and not overwrite:
            return False, f"Preset '{preset.id}' already exists. Enable overwrite to replace."

        self.storage_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Atomic write via temporary file
            temp_file = target_file.with_suffix(".tmp")
            data = preset.to_dict()
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                import os
                os.fsync(f.fileno())

            temp_file.replace(target_file)
            return True, f"Preset '{preset.name}' saved successfully."
        except Exception as e:
            return False, f"Failed to save preset: {e}"

    def delete_preset(self, preset_id: str) -> Tuple[bool, str]:
        """Delete a custom preset from the user storage directory."""
        target_file = self.storage_dir / f"{preset_id}.json"
        if not target_file.is_file():
            # Check if user tried to delete a builtin
            for p in get_curated_layout_presets():
                if p.id == preset_id:
                    return False, "Built-in presets cannot be deleted."
            return False, f"Preset '{preset_id}' not found."

        try:
            target_file.unlink()
            return True, f"Preset '{preset_id}' deleted."
        except Exception as e:
            return False, f"Failed to delete preset: {e}"

    def export_preset(self, preset_id: str, target_file: Path) -> Tuple[bool, str]:
        """Export a preset to an external JSON file."""
        preset = self.get_preset(preset_id)
        if not preset:
            return False, f"Preset '{preset_id}' not found."

        try:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(preset.to_dict(), f, indent=2)
            return True, f"Preset exported to {target_file}"
        except Exception as e:
            return False, f"Export failed: {e}"

    def import_preset(self, source_file: Path) -> Tuple[bool, Optional[LayoutPreset], str]:
        """Import a preset from an external JSON file into user storage."""
        if not source_file.is_file():
            return False, None, f"File {source_file} does not exist."

        try:
            data = json.loads(source_file.read_text(encoding="utf-8"))
            preset = LayoutPreset.from_dict(data)
            preset.is_builtin = False

            errors = preset.validate()
            if errors:
                return False, None, f"Imported preset invalid: {'; '.join(errors)}"

            ok, msg = self.save_preset(preset, overwrite=True)
            if not ok:
                return False, None, msg

            return True, preset, f"Imported preset '{preset.name}' successfully."
        except Exception as e:
            return False, None, f"Failed to parse preset file: {e}"

    def check_missing_widgets(self, preset: LayoutPreset | str, installed_plugin_ids: Set[str] | Any) -> List[str]:
        """Return list of required widgets for preset that are missing on the system."""
        target_preset: Optional[LayoutPreset]
        if isinstance(preset, str):
            target_preset = self.get_preset(preset)
        else:
            target_preset = preset

        if not target_preset:
            return []

        # If installed_plugin_ids is a WidgetCatalogService or has is_widget_installed
        if hasattr(installed_plugin_ids, "is_widget_installed"):
            return [req for req in target_preset.required_widgets if not installed_plugin_ids.is_widget_installed(req)]

        missing: List[str] = []
        for req in target_preset.required_widgets:
            req_clean = req.replace("org.kde.plasma.", "").replace("org.kde.", "")
            found = False
            for inst in installed_plugin_ids:
                inst_clean = str(inst).replace("org.kde.plasma.", "").replace("org.kde.", "")
                if inst == req or inst_clean == req_clean:
                    found = True
                    break
            if not found:
                missing.append(req)
        return missing
