"""Theme preset data models, validation, curated presets, and persistent JSON storage."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

SCHEMA_VERSION: int = 1
MAX_PRESET_FILE_SIZE_BYTES: int = 256 * 1024  # 256 KB
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-]+$")
HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")

FORBIDDEN_KEYS: Set[str] = {
    "exec", "command", "script", "shell", "run", "cmd", "eval", "system",
    "subprocess", "path", "executable", "post_install", "pre_install"
}


def slugify_name(name: str) -> str:
    """Generate a safe, alphanumeric ID from a human-readable preset name."""
    clean = re.sub(r"[^a-zA-Z0-9_\-]+", "_", name.strip().lower()).strip("_")
    return clean or "custom_theme"


class ThemeValidationError(ValueError):
    """Raised when a theme preset fails validation."""


@dataclass
class ThemeColors:
    """Palette roles for Theme Studio: primary, background, surface, text, and secondary text."""

    primary: str = "#14b8a6"
    background: str = "#131518"
    surface: str = "#181b20"
    text: str = "#f3f4f6"
    secondary_text: str = "#9ca3af"

    def validate(self) -> List[str]:
        errors: List[str] = []
        for key, val in [
            ("primary", self.primary),
            ("background", self.background),
            ("surface", self.surface),
            ("text", self.text),
            ("secondary_text", self.secondary_text),
        ]:
            if not isinstance(val, str) or not HEX_COLOR_PATTERN.match(val):
                errors.append(f"Invalid hex color value '{val}' for '{key}'.")
        return errors

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ThemeColors:
        return cls(
            primary=str(data.get("primary", data.get("accent", "#14b8a6"))),
            background=str(data.get("background", data.get("bg", "#131518"))),
            surface=str(data.get("surface", "#181b20")),
            text=str(data.get("text", data.get("textPrimary", "#f3f4f6"))),
            secondary_text=str(data.get("secondary_text", data.get("secondaryText", "#9ca3af"))),
        )


@dataclass
class ThemeTypography:
    """Typography settings for Theme Studio: supported font family and base font size."""

    font_family: str = "Inter"
    font_size: int = 13

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.font_family or not isinstance(self.font_family, str):
            errors.append("Font family must be a non-empty string.")
        elif len(self.font_family) > 120:
            errors.append(f"Font family name exceeds maximum length (120 chars).")

        if not isinstance(self.font_size, int) or not (9 <= self.font_size <= 24):
            errors.append(f"Font size {self.font_size} out of allowable bounds (9-24 pt).")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ThemeTypography:
        try:
            sz = int(data.get("font_size", data.get("fontSize", 13)))
        except (ValueError, TypeError):
            sz = 13
        return cls(
            font_family=str(data.get("font_family", data.get("fontFamily", "Inter"))).strip() or "Inter",
            font_size=sz,
        )


@dataclass
class ThemePreset:
    """Complete, versioned JSON preset for Theme Studio."""

    id: str
    name: str
    description: str = ""
    colors: ThemeColors = field(default_factory=ThemeColors)
    typography: ThemeTypography = field(default_factory=ThemeTypography)
    border_radius: int = 6
    spacing_scale: float = 1.0
    schema_version: int = SCHEMA_VERSION
    is_builtin: bool = False

    def validate(self) -> List[str]:
        errors: List[str] = []
        if self.schema_version != SCHEMA_VERSION:
            errors.append(
                f"Unsupported schema version '{self.schema_version}'. Supported version is {SCHEMA_VERSION}."
            )
        if not self.id or not SAFE_ID_PATTERN.match(self.id):
            errors.append(f"Invalid preset ID '{self.id}': must be alphanumeric with underscores or dashes.")
        if not self.name or len(self.name) > 100:
            errors.append("Preset name must be non-empty and under 100 characters.")

        errors.extend(self.colors.validate())
        errors.extend(self.typography.validate())

        if not isinstance(self.border_radius, int) or not (0 <= self.border_radius <= 32):
            errors.append(f"Border radius {self.border_radius} out of bounds (0-32px).")

        if not isinstance(self.spacing_scale, (int, float)) or not (0.5 <= float(self.spacing_scale) <= 2.5):
            errors.append(f"Spacing scale {self.spacing_scale} out of bounds (0.5-2.5).")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "colors": self.colors.to_dict(),
            "typography": self.typography.to_dict(),
            "border_radius": self.border_radius,
            "spacing_scale": round(float(self.spacing_scale), 2),
            "is_builtin": self.is_builtin,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], is_builtin: bool = False) -> ThemePreset:
        for k in data.keys():
            if k.lower() in FORBIDDEN_KEYS:
                raise ThemeValidationError(f"Forbidden key '{k}' detected in theme preset.")

        schema_ver = int(data.get("schema_version", 1))
        if schema_ver != SCHEMA_VERSION:
            raise ThemeValidationError(
                f"Unsupported theme preset schema version {schema_ver}. Supported version is {SCHEMA_VERSION}."
            )

        colors_dict = data.get("colors")
        if not isinstance(colors_dict, dict):
            colors_dict = {}

        typo_dict = data.get("typography")
        if not isinstance(typo_dict, dict):
            typo_dict = {}

        try:
            radius = int(data.get("border_radius", data.get("borderRadius", 6)))
        except (ValueError, TypeError):
            radius = 6

        try:
            scale = float(data.get("spacing_scale", data.get("spacingScale", 1.0)))
        except (ValueError, TypeError):
            scale = 1.0

        preset = cls(
            id=str(data.get("id", "")).strip(),
            name=str(data.get("name", "")).strip(),
            description=str(data.get("description", "")).strip(),
            colors=ThemeColors.from_dict(colors_dict),
            typography=ThemeTypography.from_dict(typo_dict),
            border_radius=radius,
            spacing_scale=scale,
            schema_version=schema_ver,
            is_builtin=is_builtin,
        )

        validation_errors = preset.validate()
        if validation_errors:
            raise ThemeValidationError(f"Preset validation failed: {'; '.join(validation_errors)}")

        return preset


def get_builtin_theme_presets() -> List[ThemePreset]:
    """Curated built-in theme presets provided out-of-the-box."""
    return [
        ThemePreset(
            id="plasmaforge_teal",
            name="PlasmaForge Teal (Default)",
            description="The signature PlasmaForge dark slate theme with vibrant teal accents and balanced spacing.",
            colors=ThemeColors(
                primary="#14b8a6",
                background="#131518",
                surface="#181b20",
                text="#f3f4f6",
                secondary_text="#9ca3af",
            ),
            typography=ThemeTypography(font_family="Inter", font_size=13),
            border_radius=6,
            spacing_scale=1.0,
            is_builtin=True,
        ),
        ThemePreset(
            id="nordic_horizon",
            name="Nordic Horizon",
            description="Cool arctic dark slate with polar blue highlights and soft contrasts.",
            colors=ThemeColors(
                primary="#88c0d0",
                background="#242933",
                surface="#2e3440",
                text="#eceff4",
                secondary_text="#d8dee9",
            ),
            typography=ThemeTypography(font_family="Inter", font_size=13),
            border_radius=8,
            spacing_scale=1.0,
            is_builtin=True,
        ),
        ThemePreset(
            id="arch_minimalist",
            name="Arch Cyan",
            description="Sharp, distraction-free charcoal and Arch Linux cyan with compact density.",
            colors=ThemeColors(
                primary="#1793d1",
                background="#121417",
                surface="#1c1f24",
                text="#f5f5f5",
                secondary_text="#9ca3af",
            ),
            typography=ThemeTypography(font_family="Noto Sans", font_size=12),
            border_radius=4,
            spacing_scale=0.85,
            is_builtin=True,
        ),
        ThemePreset(
            id="paper_umber",
            name="Paper & Umber",
            description="Warm earthen palette designed to minimize eye strain during long reading sessions.",
            colors=ThemeColors(
                primary="#d97706",
                background="#1e1d1b",
                surface="#2a2825",
                text="#e7e5e4",
                secondary_text="#a8a29e",
            ),
            typography=ThemeTypography(font_family="Cantarell", font_size=14),
            border_radius=10,
            spacing_scale=1.15,
            is_builtin=True,
        ),
        ThemePreset(
            id="monochrome_matrix",
            name="Monochrome Studio",
            description="High-contrast grayscale workstation palette with crisp emerald status highlights.",
            colors=ThemeColors(
                primary="#10b981",
                background="#0f1115",
                surface="#181a20",
                text="#ffffff",
                secondary_text="#8b949e",
            ),
            typography=ThemeTypography(font_family="JetBrains Mono", font_size=13),
            border_radius=6,
            spacing_scale=1.0,
            is_builtin=True,
        ),
    ]


class ThemePresetManager:
    """Manages discovery, saving, loading, deletion, and importing of Theme Studio presets."""

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        if storage_dir is not None:
            self.storage_dir = storage_dir
        else:
            xdg_data = os.environ.get("XDG_DATA_HOME")
            if xdg_data:
                self.storage_dir = Path(xdg_data) / "plasmaforge" / "theme_presets"
            else:
                self.storage_dir = Path.home() / ".local" / "share" / "plasmaforge" / "theme_presets"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._builtin_presets = {p.id: p for p in get_builtin_theme_presets()}

    def list_presets(self) -> List[ThemePreset]:
        """Return combined list of built-in presets and valid user-created presets."""
        presets: Dict[str, ThemePreset] = dict(self._builtin_presets)

        if self.storage_dir.is_dir():
            for p in sorted(self.storage_dir.glob("*.json")):
                try:
                    if p.stat().st_size > MAX_PRESET_FILE_SIZE_BYTES:
                        continue
                    text = p.read_text(encoding="utf-8")
                    data = json.loads(text)
                    preset = ThemePreset.from_dict(data, is_builtin=False)
                    presets[preset.id] = preset
                except Exception:
                    # Gracefully skip malformed, incompatible, or corrupted files
                    continue

        return list(presets.values())

    def get_preset(self, preset_id: str) -> Optional[ThemePreset]:
        """Retrieve a preset by identifier."""
        for p in self.list_presets():
            if p.id == preset_id:
                return p
        return None

    def save_preset(self, preset: ThemePreset, overwrite: bool = False) -> tuple[bool, str]:
        """Persist a theme preset to JSON in the user data directory."""
        errors = preset.validate()
        if errors:
            return False, f"Preset validation failed: {'; '.join(errors)}"

        if preset.id in self._builtin_presets:
            return False, f"Cannot overwrite built-in preset '{preset.name}'. Please choose a different name."

        file_path = self.storage_dir / f"{preset.id}.json"
        if file_path.is_file() and not overwrite:
            return False, f"Preset '{preset.name}' already exists. Confirm overwrite to replace."

        try:
            temp_file = file_path.with_suffix(".tmp")
            data = preset.to_dict()
            data["is_builtin"] = False
            temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            temp_file.replace(file_path)
            return True, f"Preset '{preset.name}' saved successfully."
        except Exception as e:
            return False, f"Failed to save preset: {e}"

    def delete_preset(self, preset_id: str) -> tuple[bool, str]:
        """Delete a user-created preset file."""
        if preset_id in self._builtin_presets:
            return False, "Cannot delete built-in presets."

        file_path = self.storage_dir / f"{preset_id}.json"
        if not file_path.is_file():
            return False, f"Preset file '{preset_id}' not found."

        try:
            file_path.unlink()
            return True, "Preset deleted successfully."
        except Exception as e:
            return False, f"Failed to delete preset: {e}"

    def import_preset_json(self, json_str: str) -> tuple[bool, str, Optional[ThemePreset]]:
        """Validate and import a JSON preset string without mutating system configuration."""
        if not json_str or not json_str.strip():
            return False, "Cannot import empty preset data.", None

        if len(json_str.encode("utf-8")) > MAX_PRESET_FILE_SIZE_BYTES:
            return False, f"Preset exceeds {MAX_PRESET_FILE_SIZE_BYTES // 1024} KB limit.", None

        try:
            data = json.loads(json_str)
        except Exception as e:
            return False, f"Malformed JSON: {e}", None

        if not isinstance(data, dict):
            return False, "Preset root must be a JSON object.", None

        try:
            preset = ThemePreset.from_dict(data, is_builtin=False)
        except Exception as e:
            return False, f"Invalid preset format: {e}", None

        # Avoid clashing with built-in IDs
        if preset.id in self._builtin_presets:
            preset.id = f"{preset.id}_imported"

        ok, msg = self.save_preset(preset, overwrite=True)
        return ok, msg, (preset if ok else None)

    def import_preset_file(self, file_path: Path) -> tuple[bool, str, Optional[ThemePreset]]:
        """Import preset from a file path."""
        if not file_path.is_file():
            return False, f"File does not exist: {file_path}", None
        try:
            content = file_path.read_text(encoding="utf-8")
            return self.import_preset_json(content)
        except Exception as e:
            return False, f"Error reading file: {e}", None

    def export_preset(self, preset_id: str, dest_path: Path) -> tuple[bool, str]:
        """Export preset to JSON at destination path."""
        preset = self.get_preset(preset_id)
        if not preset:
            return False, f"Preset '{preset_id}' not found."
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            data = preset.to_dict()
            dest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return True, f"Preset exported to {dest_path.name}"
        except Exception as e:
            return False, f"Export failed: {e}"
