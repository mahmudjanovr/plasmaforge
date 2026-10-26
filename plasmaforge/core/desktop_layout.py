"""Desktop layout data models, preset registry, detection, and transactional layout applier for KDE Plasma 6."""

from __future__ import annotations

import configparser
import difflib
import io
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from plasmaforge.core.backup_manager import BackupManager
from plasmaforge.core.kde_panel_editor import KdePanelLiveEditor
from plasmaforge.core.transaction import (
    ApplyOperation,
    TransactionalSafetyEngine,
    TransactionResult,
    TransactionState,
)


class PanelPosition(str, Enum):
    """Panel edge anchor position."""

    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    NONE = "none"


class PanelVisibility(str, Enum):
    """Panel auto-hide or overlay behavior."""

    ALWAYS_VISIBLE = "always_visible"
    AUTO_HIDE = "auto_hide"
    DODGE_WINDOWS = "dodge_windows"
    WINDOWS_GO_BELOW = "windows_go_below"
    WINDOWS_BELOW = "windows_below"


LOCATION_TO_POS: Dict[int, str] = {
    0: "floating",
    1: "left",
    2: "right",
    3: "top",
    4: "bottom",
}

POS_TO_LOCATION: Dict[str, int] = {
    "left": 1,
    "right": 2,
    "top": 3,
    "bottom": 4,
}

VISIBILITY_TO_NAME: Dict[int, str] = {
    0: "always_visible",
    1: "auto_hide",
    2: "dodge_windows",
    3: "windows_go_below",
}

NAME_TO_VISIBILITY: Dict[str, int] = {
    "always_visible": 0,
    "auto_hide": 1,
    "dodge_windows": 2,
    "windows_go_below": 3,
    "windows_below": 3,
}


@dataclass
class PanelConfig:
    """Configuration for a specific KDE Plasma panel or dock."""

    position: str = "bottom"  # top, bottom, left, right, none
    thickness: int = 36       # height/width in pixels
    visibility: str = "always_visible"  # always_visible, auto_hide, dodge_windows
    is_dock: bool = False
    icon_size: int = 40       # icon size in px (for docks/tasks)
    applets: List[str] = field(default_factory=list)
    containment_id: Optional[str] = None
    is_detected: bool = False

    def validate(self) -> List[str]:
        """Validate panel parameters."""
        errors: List[str] = []
        valid_positions = {p.value for p in PanelPosition}
        if self.position not in valid_positions:
            errors.append(f"Invalid panel position '{self.position}'. Allowed: {valid_positions}")

        if not (16 <= self.thickness <= 128):
            errors.append(f"Panel thickness {self.thickness}px out of bounds (16-128px).")

        valid_vis = {v.value for v in PanelVisibility}
        if self.visibility not in valid_vis:
            errors.append(f"Invalid visibility mode '{self.visibility}'. Allowed: {valid_vis}")

        if not (16 <= self.icon_size <= 96):
            errors.append(f"Icon size {self.icon_size}px out of bounds (16-96px).")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PanelConfig:
        return cls(
            position=str(data.get("position", "bottom")),
            thickness=int(data.get("thickness", 36)),
            visibility=str(data.get("visibility", "always_visible")),
            is_dock=bool(data.get("is_dock", False)),
            icon_size=int(data.get("icon_size", 40)),
            applets=[str(a) for a in data.get("applets", [])],
            containment_id=str(data["containment_id"]) if data.get("containment_id") else None,
            is_detected=bool(data.get("is_detected", False)),
        )


@dataclass
class DesktopLayout:
    """Full desktop blueprint containing panel, dock, and widget orchestration."""

    id: str
    name: str
    description: str
    top_panel: PanelConfig = field(default_factory=lambda: PanelConfig(position="top", thickness=32))
    dock: PanelConfig = field(default_factory=lambda: PanelConfig(position="bottom", thickness=48, is_dock=True))
    show_widgets: bool = False
    is_detected: bool = False
    is_preset: bool = False

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.name.strip():
            errors.append("Layout name cannot be empty.")
        errors.extend([f"Top panel: {e}" for e in self.top_panel.validate()])
        errors.extend([f"Dock: {e}" for e in self.dock.validate()])
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "top_panel": self.top_panel.to_dict(),
            "dock": self.dock.to_dict(),
            "show_widgets": self.show_widgets,
            "is_detected": self.is_detected,
            "is_preset": self.is_preset,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DesktopLayout:
        return cls(
            id=str(data.get("id", "custom")),
            name=str(data.get("name", "Custom Layout")),
            description=str(data.get("description", "")),
            top_panel=PanelConfig.from_dict(data.get("top_panel", {})),
            dock=PanelConfig.from_dict(data.get("dock", {})),
            show_widgets=bool(data.get("show_widgets", False)),
            is_detected=bool(data.get("is_detected", False)),
            is_preset=bool(data.get("is_preset", False)),
        )


def get_layout_presets() -> List[DesktopLayout]:
    """sensible curated layout presets."""
    return [
        DesktopLayout(
            id="classic_kde",
            name="Classic KDE",
            description="Conventional full-width bottom panel containing app launcher, task manager, and system tray.",
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
                applets=["kickoff", "taskmanager", "systemtray", "digitalclock"],
            ),
            show_widgets=False,
            is_preset=True,
        ),
        DesktopLayout(
            id="nothing_inspired",
            name="Nothing-Inspired",
            description="Minimalist dual arrangement: sleek top status bar and centered floating bottom dock.",
            top_panel=PanelConfig(
                position="top",
                thickness=32,
                visibility="always_visible",
                applets=["kickoff", "appmenu", "digitalclock", "systemtray"],
            ),
            dock=PanelConfig(
                position="bottom",
                thickness=52,
                visibility="dodge_windows",
                is_dock=True,
                icon_size=44,
                applets=["icontasks"],
            ),
            show_widgets=True,
            is_preset=True,
        ),
        DesktopLayout(
            id="clean_minimal",
            name="Clean Minimal",
            description="Distraction-free auto-hiding layout maximizing active workspace real estate.",
            top_panel=PanelConfig(
                position="top",
                thickness=30,
                visibility="auto_hide",
                applets=["systemtray", "digitalclock"],
            ),
            dock=PanelConfig(
                position="bottom",
                thickness=46,
                visibility="auto_hide",
                is_dock=True,
                icon_size=38,
                applets=["icontasks"],
            ),
            show_widgets=False,
            is_preset=True,
        ),
    ]


def detect_desktop_layout(config_path: Optional[Path] = None) -> DesktopLayout:
    """Inspect ~/.config/plasma-org.kde.plasma.desktop-appletsrc to detect active panel geometry."""
    appletsrc_path = config_path or (
        Path.home() / ".config" / "plasma-org.kde.plasma.desktop-appletsrc"
    )

    default_layout = DesktopLayout(
        id="detected_active",
        name="Detected KDE Desktop",
        description="Active desktop layout detected from KDE Plasma configuration.",
        top_panel=PanelConfig(position="top", thickness=36, visibility="always_visible", is_detected=False),
        dock=PanelConfig(position="bottom", thickness=48, visibility="always_visible", is_dock=True, is_detected=False),
        show_widgets=False,
        is_detected=True,
    )

    if not appletsrc_path.is_file():
        return default_layout

    try:
        content = appletsrc_path.read_text(encoding="utf-8", errors="replace")
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read_string(content)

        top_panel: Optional[PanelConfig] = None
        dock: Optional[PanelConfig] = None
        has_widgets = False

        # Find containments
        containment_sections = [
            s for s in parser.sections() if s.startswith("Containments][") and s.count("][") == 1
        ]

        for sec in containment_sections:
            cid = sec.split("][")[1].rstrip("]")
            plugin = parser.get(sec, "plugin", fallback="")

            if plugin == "org.kde.panel":
                location_code = parser.getint(sec, "location", fallback=4)
                pos = LOCATION_TO_POS.get(location_code, "bottom")

                # Check visibility
                vis_code = parser.getint(sec, "visibility", fallback=0)
                visibility = VISIBILITY_TO_NAME.get(vis_code, "always_visible")

                # Thickness
                thickness = 36
                if parser.has_option(sec, "thickness"):
                    thickness = parser.getint(sec, "thickness", fallback=36)
                elif parser.has_section(f"Containments][{cid}][ConfigDialog"):
                    h = parser.getint(f"Containments][{cid}][ConfigDialog", "DialogHeight", fallback=36)
                    if 20 <= h <= 128:
                        thickness = h
                elif parser.has_section(f"Containments][{cid}][ConfigDialog]"):
                    h = parser.getint(f"Containments][{cid}][ConfigDialog]", "DialogHeight", fallback=36)
                    if 20 <= h <= 128:
                        thickness = h

                # Applets
                applets: List[str] = []
                for s in parser.sections():
                    if s.startswith(f"Containments][{cid}][Applets][") and s.count("][") == 3:
                        plug = parser.get(s, "plugin", fallback="")
                        if plug:
                            applets.append(plug.replace("org.kde.plasma.", ""))

                is_dock_panel = ("icontasks" in applets) or (pos == "bottom" and len(applets) <= 3)

                panel_cfg = PanelConfig(
                    position=pos,
                    thickness=thickness,
                    visibility=visibility,
                    is_dock=is_dock_panel,
                    icon_size=int(thickness * 0.8),
                    applets=applets,
                    containment_id=cid,
                    is_detected=True,
                )

                if pos == "top" and top_panel is None:
                    top_panel = panel_cfg
                elif is_dock_panel and dock is None:
                    dock = panel_cfg
                elif dock is None:
                    dock = panel_cfg
                elif top_panel is None:
                    top_panel = panel_cfg

            elif plugin == "org.kde.plasma.folder":
                # Desktop wallpaper & desktop applets containment
                for s in parser.sections():
                    if s.startswith(f"Containments][{cid}][Applets][") and s.count("][") == 3:
                        has_widgets = True

        return DesktopLayout(
            id="detected_active",
            name="Detected KDE Desktop",
            description="Active desktop layout detected from live KDE configuration.",
            top_panel=top_panel or PanelConfig(position="none", thickness=32, is_detected=False),
            dock=dock or PanelConfig(position="bottom", thickness=44, is_dock=True, is_detected=False),
            show_widgets=has_widgets,
            is_detected=True,
        )

    except Exception:
        return default_layout


class DesktopLayoutApplier:
    """Manages diff generation, transactional execution, and rollback for KDE desktop layouts."""

    def __init__(
        self,
        backup_manager: Optional[BackupManager] = None,
        safe_mode: bool = True,
        source_config_dir: Optional[Path] = None,
        live_editor: Optional[KdePanelLiveEditor] = None,
    ) -> None:
        self.backup_manager = backup_manager or BackupManager()
        self.safe_mode = safe_mode
        self.source_config_dir = source_config_dir or (Path.home() / ".config")
        self.safety_engine = TransactionalSafetyEngine(
            backup_manager=self.backup_manager,
            safe_mode=self.safe_mode,
            source_config_dir=self.source_config_dir,
        )
        self.live_editor = live_editor or KdePanelLiveEditor()

    def generate_diff_preview(self, target_layout: DesktopLayout) -> str:
        """Generate unified diff showing what ~/.config/plasma-org.kde.plasma.desktop-appletsrc would change."""
        config_file = self.source_config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
        current_text = ""
        if config_file.is_file():
            try:
                current_text = config_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                current_text = ""

        try:
            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str
            if current_text:
                parser.read_string(current_text)

            detected = detect_desktop_layout(config_file)

            # Apply top panel changes
            if detected.top_panel.containment_id:
                cid = detected.top_panel.containment_id
                sec = f"Containments][{cid}"
                if not parser.has_section(sec):
                    parser.add_section(sec)

                loc = POS_TO_LOCATION.get(target_layout.top_panel.position, 3)
                parser.set(sec, "location", str(loc))

                vis = NAME_TO_VISIBILITY.get(target_layout.top_panel.visibility, 0)
                parser.set(sec, "visibility", str(vis))
                parser.set(sec, "thickness", str(target_layout.top_panel.thickness))

            # Apply dock changes
            if detected.dock.containment_id:
                cid = detected.dock.containment_id
                sec = f"Containments][{cid}"
                if not parser.has_section(sec):
                    parser.add_section(sec)

                loc = POS_TO_LOCATION.get(target_layout.dock.position, 4)
                parser.set(sec, "location", str(loc))

                vis = NAME_TO_VISIBILITY.get(target_layout.dock.visibility, 0)
                parser.set(sec, "visibility", str(vis))
                parser.set(sec, "thickness", str(target_layout.dock.thickness))

            buf = io.StringIO()
            parser.write(buf)
            new_text = buf.getvalue()

            diff_lines = list(
                difflib.unified_diff(
                    current_text.splitlines(keepends=True),
                    new_text.splitlines(keepends=True),
                    fromfile="a/~/.config/plasma-org.kde.plasma.desktop-appletsrc (current)",
                    tofile=f"b/~/.config/plasma-org.kde.plasma.desktop-appletsrc ({target_layout.name})",
                    n=2,
                )
            )

            dbus_status = (
                "Supported (org.kde.PlasmaShell evaluateScript)"
                if self.live_editor.is_live_dbus_supported()
                else "Unavailable (deferred to session reload)"
            )

            header = [
                f"# Unified Diff Preview: Desktop Layout '{target_layout.name}'",
                f"# Target: {config_file}",
                f"# Live D-Bus apply: {dbus_status}",
                f"# Supported live properties: panel position, thickness, visibility",
                f"# Note: Widget placement, dock icon size, and floating dock padding are preview-only simulations.",
                "--------------------------------------------------\n",
            ]

            if not diff_lines:
                return "".join(header + ["# Configuration keys already match the draft layout. No changes required."])

            return "".join(header + diff_lines[:140])

        except Exception as e:
            return f"Failed to compute diff: {e}"

    def apply_layout(
        self,
        target_layout: DesktopLayout,
        force_safe_mode: Optional[bool] = None,
    ) -> TransactionResult:
        """Apply layout safely using transactional boundary and live D-Bus updates."""
        errors = target_layout.validate()
        if errors:
            return TransactionResult(
                success=False,
                state=TransactionState.ABORTED,
                message=f"Layout validation failed: {'; '.join(errors)}",
                operation_id=f"apply_layout_{target_layout.id}",
                affected_files=["plasma-org.kde.plasma.desktop-appletsrc"],
            )

        is_safe = self.safe_mode if force_safe_mode is None else force_safe_mode
        config_file = self.source_config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
        diff_text = self.generate_diff_preview(target_layout)

        live_revert_states: Dict[str, Dict[str, Any]] = {}
        applied_live_containments: List[str] = []

        def apply_step() -> tuple[bool, str]:
            try:
                parser = configparser.ConfigParser(interpolation=None)
                parser.optionxform = str
                if config_file.is_file():
                    parser.read(config_file, encoding="utf-8")

                detected = detect_desktop_layout(config_file)

                # Ensure containment IDs are resolved if not explicitly provided
                if not target_layout.top_panel.containment_id and detected.top_panel.containment_id:
                    target_layout.top_panel.containment_id = detected.top_panel.containment_id
                if not target_layout.dock.containment_id and detected.dock.containment_id:
                    target_layout.dock.containment_id = detected.dock.containment_id

                # Update top panel on disk
                if target_layout.top_panel.containment_id and target_layout.top_panel.position != "none":
                    cid = target_layout.top_panel.containment_id
                    sec = f"Containments][{cid}"
                    if not parser.has_section(sec):
                        parser.add_section(sec)
                    loc = POS_TO_LOCATION.get(target_layout.top_panel.position, 3)
                    vis = NAME_TO_VISIBILITY.get(target_layout.top_panel.visibility, 0)
                    parser.set(sec, "location", str(loc))
                    parser.set(sec, "visibility", str(vis))
                    parser.set(sec, "thickness", str(target_layout.top_panel.thickness))

                # Update dock on disk
                if target_layout.dock.containment_id and target_layout.dock.position != "none":
                    cid = target_layout.dock.containment_id
                    sec = f"Containments][{cid}"
                    if not parser.has_section(sec):
                        parser.add_section(sec)
                    loc = POS_TO_LOCATION.get(target_layout.dock.position, 4)
                    vis = NAME_TO_VISIBILITY.get(target_layout.dock.visibility, 0)
                    parser.set(sec, "location", str(loc))
                    parser.set(sec, "visibility", str(vis))
                    parser.set(sec, "thickness", str(target_layout.dock.thickness))

                config_file.parent.mkdir(parents=True, exist_ok=True)
                with open(config_file, "w", encoding="utf-8") as f:
                    parser.write(f, space_around_delimiters=False)

                # Live D-Bus apply (if supported and not in safe mode)
                if not is_safe and self.live_editor.is_live_dbus_supported():
                    panels_to_edit: List[PanelConfig] = []
                    if target_layout.top_panel.containment_id and target_layout.top_panel.position != "none":
                        panels_to_edit.append(target_layout.top_panel)
                    if target_layout.dock.containment_id and target_layout.dock.position != "none":
                        panels_to_edit.append(target_layout.dock)

                    for p_cfg in panels_to_edit:
                        cid = p_cfg.containment_id
                        assert cid is not None
                        ok_live, audit, msg = self.live_editor.apply_panel_properties(
                            containment_id=cid,
                            location=p_cfg.position,
                            height=p_cfg.thickness,
                            visibility=p_cfg.visibility,
                        )
                        if ok_live:
                            if "previous" in audit:
                                live_revert_states[cid] = audit["previous"]
                            applied_live_containments.append(cid)
                        else:
                            return False, f"Live application failed on panel #{cid}: {msg}"

                    if applied_live_containments:
                        return (
                            True,
                            f"Applied live via D-Bus and saved to disk (panels: {', '.join(applied_live_containments)}).",
                        )

                return (
                    True,
                    "Layout settings saved to plasma-org.kde.plasma.desktop-appletsrc. Visual changes will apply on desktop refresh or next login.",
                )
            except Exception as e:
                return False, f"Failed to write layout configuration: {e}"

        def verify_step() -> tuple[bool, str]:
            if not config_file.is_file():
                return False, "Target configuration file missing after apply."
            try:
                # 1. Verify disk persistence
                verified_layout = detect_desktop_layout(config_file)
                if target_layout.top_panel.containment_id and target_layout.top_panel.position != "none":
                    if verified_layout.top_panel.position != target_layout.top_panel.position:
                        return False, f"Verification failed: top panel position is '{verified_layout.top_panel.position}', expected '{target_layout.top_panel.position}'"

                if target_layout.dock.containment_id and target_layout.dock.position != "none":
                    if verified_layout.dock.position != target_layout.dock.position:
                        return False, f"Verification failed: dock position is '{verified_layout.dock.position}', expected '{target_layout.dock.position}'"

                # 2. Verify live D-Bus state if live apply was performed
                if applied_live_containments and not is_safe and self.live_editor.is_live_dbus_supported():
                    panels_to_verify: List[PanelConfig] = []
                    if target_layout.top_panel.containment_id in applied_live_containments:
                        panels_to_verify.append(target_layout.top_panel)
                    if target_layout.dock.containment_id in applied_live_containments:
                        panels_to_verify.append(target_layout.dock)

                    for p_cfg in panels_to_verify:
                        assert p_cfg.containment_id is not None
                        ok_v, v_msg = self.live_editor.verify_panel_properties(
                            containment_id=p_cfg.containment_id,
                            expected_location=p_cfg.position,
                            expected_height=p_cfg.thickness,
                            expected_visibility=p_cfg.visibility,
                        )
                        if not ok_v:
                            return False, f"Live verification failed: {v_msg}"

                return True, "Layout configuration verified on disk and live desktop."
            except Exception as e:
                return False, f"Verification error: {e}"

        operation = ApplyOperation(
            id=f"apply_layout_{target_layout.id}",
            title=f"Apply Desktop Layout '{target_layout.name}'",
            description=f"Applies panel geometry and visibility for '{target_layout.name}' to plasma-org.kde.plasma.desktop-appletsrc",
            affected_files=["plasma-org.kde.plasma.desktop-appletsrc"],
            diff_preview=diff_text,
            apply_fn=apply_step,
            verify_fn=verify_step,
        )

        self.safety_engine.safe_mode = self.safe_mode
        self.safety_engine.source_config_dir = self.source_config_dir
        res = self.safety_engine.execute(
            operation,
            confirmed=True,
            force_safe_mode=force_safe_mode,
        )

        # On failure, revert live D-Bus state if any panels were modified live
        if not res.success and live_revert_states:
            for cid, prev_state in live_revert_states.items():
                self.live_editor.revert_panel_properties(cid, prev_state)

        return res
