"""Validated, versioned setup profile models, curated gallery collection, and storage management."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from plasmaforge.core.desktop_layout import DesktopLayout, PanelConfig

SCHEMA_VERSION: int = 1
MAX_PROFILE_FILE_SIZE_BYTES: int = 512 * 1024  # 512 KB
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-]+$")
SAFE_SCHEME_PATTERN = re.compile(r"^[A-Za-z0-9_\-\.\s]+$")

# Disallowed keys to prevent command injection or arbitrary code execution in profiles
FORBIDDEN_KEYS: Set[str] = {
    "exec", "command", "script", "shell", "run", "cmd", "eval", "system",
    "subprocess", "path", "executable", "post_install", "pre_install"
}


class ProfileValidationError(ValueError):
    """Raised when a profile fails schema or safety validation."""


@dataclass
class ColorSchemeSpec:
    """Color scheme reference and preview swatches for a setup profile."""

    scheme_id: str
    name: str = ""
    preview_colors: Dict[str, str] = field(default_factory=dict)

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.scheme_id or not self.scheme_id.strip():
            errors.append("Color scheme ID cannot be empty.")
        elif not SAFE_SCHEME_PATTERN.match(self.scheme_id):
            errors.append(f"Color scheme ID '{self.scheme_id}' contains forbidden characters.")

        # Validate hex color strings if provided
        for k, col in self.preview_colors.items():
            if not isinstance(col, str) or not re.match(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$", col):
                errors.append(f"Invalid preview color value '{col}' for key '{k}'.")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ColorSchemeSpec:
        return cls(
            scheme_id=str(data.get("scheme_id", "BreezeDark")),
            name=str(data.get("name", data.get("scheme_id", "Breeze Dark"))),
            preview_colors=dict(data.get("preview_colors", {})),
        )


@dataclass
class SetupProfile:
    """Unified setup profile combining KDE color scheme, desktop layout, and metadata."""

    id: str
    name: str
    tagline: str
    description: str
    author: str
    version: str
    category: str
    tags: List[str]
    color_scheme: ColorSchemeSpec
    desktop_layout: DesktopLayout
    simulated_features: Dict[str, str] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION
    is_user_imported: bool = False

    def validate(self) -> List[str]:
        """Perform comprehensive schema and safety checks."""
        errors: List[str] = []

        if self.schema_version != SCHEMA_VERSION:
            errors.append(f"Unsupported schema version '{self.schema_version}'. Supported: [{SCHEMA_VERSION}].")

        if not self.id or not SAFE_ID_PATTERN.match(self.id):
            errors.append(f"Invalid profile ID '{self.id}': must be alphanumeric with underscores or dashes.")

        if not self.name or len(self.name) > 100:
            errors.append("Profile name must be non-empty and under 100 characters.")

        if not self.category:
            errors.append("Profile category cannot be empty.")

        errors.extend(self.color_scheme.validate())
        errors.extend(self.desktop_layout.validate())

        # Check for forbidden executable injection keys in simulated features
        for k in self.simulated_features.keys():
            if k.lower() in FORBIDDEN_KEYS:
                errors.append(f"Forbidden key '{k}' detected in simulated features.")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "name": self.name,
            "tagline": self.tagline,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "category": self.category,
            "tags": list(self.tags),
            "color_scheme": self.color_scheme.to_dict(),
            "desktop_layout": self.desktop_layout.to_dict(),
            "simulated_features": dict(self.simulated_features),
            "is_user_imported": self.is_user_imported,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], is_imported: bool = False) -> SetupProfile:
        # Check forbidden root keys
        for k in data.keys():
            if k.lower() in FORBIDDEN_KEYS:
                raise ProfileValidationError(f"Forbidden executable key '{k}' detected in profile root.")

        schema_ver = int(data.get("schema_version", 1))
        if schema_ver != SCHEMA_VERSION:
            raise ProfileValidationError(
                f"Unsupported profile schema version {schema_ver}. Supported version is {SCHEMA_VERSION}."
            )

        if "color_scheme" not in data or not isinstance(data["color_scheme"], dict):
            raise ProfileValidationError("Profile missing required 'color_scheme' section.")

        if "desktop_layout" not in data or not isinstance(data["desktop_layout"], dict):
            raise ProfileValidationError("Profile missing required 'desktop_layout' section.")

        cs_data = data["color_scheme"]
        layout_data = data["desktop_layout"]

        profile = cls(
            id=str(data.get("id", "")).strip(),
            name=str(data.get("name", "")).strip(),
            tagline=str(data.get("tagline", "")).strip(),
            description=str(data.get("description", "")).strip(),
            author=str(data.get("author", "Community")).strip(),
            version=str(data.get("version", "1.0")).strip(),
            category=str(data.get("category", "Productivity")).strip(),
            tags=[str(t) for t in data.get("tags", [])],
            color_scheme=ColorSchemeSpec.from_dict(cs_data),
            desktop_layout=DesktopLayout.from_dict(layout_data),
            simulated_features=dict(data.get("simulated_features", {})),
            schema_version=schema_ver,
            is_user_imported=is_imported,
        )

        validation_errors = profile.validate()
        if validation_errors:
            raise ProfileValidationError(f"Profile validation failed: {'; '.join(validation_errors)}")

        return profile


def get_curated_profiles() -> List[SetupProfile]:
    """Return the built-in curated setup profiles."""
    return [
        SetupProfile(
            id="obsidian_teal",
            name="Obsidian Teal Studio",
            tagline="Slate dark base with electric teal highlights and crisp typography.",
            description="Engineered for focused development sessions on KDE Plasma 6. Features deep neutral backgrounds, low glare, and high legibility.",
            author="PlasmaForge Core",
            version="1.0",
            category="Productivity",
            tags=["Productivity", "Dark", "Teal", "Development"],
            color_scheme=ColorSchemeSpec(
                scheme_id="BreezeDark",
                name="Breeze Dark (Teal Accent)",
                preview_colors={
                    "bg": "#181a1f",
                    "surface": "#22252c",
                    "accent": "#14b8a6",
                    "text": "#eff0f1",
                },
            ),
            desktop_layout=DesktopLayout(
                id="obsidian_teal_layout",
                name="Obsidian Dual Layout",
                description="Top status bar with bottom dock",
                top_panel=PanelConfig(
                    position="top",
                    thickness=32,
                    visibility="always_visible",
                    applets=["kickoff", "appmenu", "digitalclock", "systemtray"],
                ),
                dock=PanelConfig(
                    position="bottom",
                    thickness=48,
                    icon_size=40,
                    visibility="always_visible",
                    is_dock=True,
                    applets=["icontasks"],
                ),
                show_widgets=False,
            ),
            simulated_features={
                "wallpaper": "Dark Abstract Teal Wave",
                "font_family": "Inter 10pt",
                "monospace_family": "JetBrains Mono 10pt",
                "widget_simulation": "Preview simulation only; fonts and wallpapers require manual setup.",
            },
        ),
        SetupProfile(
            id="nordic_horizon",
            name="Nordic Horizon",
            tagline="Cool arctic slate with soft cyan and polar blue accents.",
            description="Clean Nordic palette adapted for native Qt Quick and Plasma 6. Balanced contrast with smooth visual hierarchy.",
            author="PlasmaForge Core",
            version="1.0",
            category="Minimal",
            tags=["Nord", "Clean", "Wayland", "Minimal"],
            color_scheme=ColorSchemeSpec(
                scheme_id="BreezeClassic",
                name="Nordic Horizon Slate",
                preview_colors={
                    "bg": "#242933",
                    "surface": "#2e3440",
                    "accent": "#88c0d0",
                    "text": "#eceff4",
                },
            ),
            desktop_layout=DesktopLayout(
                id="nordic_horizon_layout",
                name="Nordic Auto-Hide Layout",
                description="Auto-hiding top panel and dock",
                top_panel=PanelConfig(
                    position="top",
                    thickness=30,
                    visibility="auto_hide",
                    applets=["systemtray", "digitalclock"],
                ),
                dock=PanelConfig(
                    position="bottom",
                    thickness=46,
                    icon_size=38,
                    visibility="auto_hide",
                    is_dock=True,
                    applets=["icontasks"],
                ),
                show_widgets=False,
            ),
            simulated_features={
                "wallpaper": "Nordic Slate Minimalist Gradient",
                "font_family": "Cantarell 10pt",
                "widget_simulation": "Preview simulation only.",
            },
        ),
        SetupProfile(
            id="nothing_inspired",
            name="Nothing-Inspired Studio",
            tagline="Monochrome glyph-oriented aesthetic with top status and floating dock.",
            description="High-contrast dot-matrix inspired layout pairing a sleek top status panel with a floating centered bottom dock and desktop telemetry.",
            author="PlasmaForge Core",
            version="1.0",
            category="Nothing-Inspired",
            tags=["Nothing-Inspired", "Monochrome", "Minimal", "Glyph"],
            color_scheme=ColorSchemeSpec(
                scheme_id="Nothing",
                name="Nothing Dark",
                preview_colors={
                    "bg": "#0a0a0c",
                    "surface": "#141418",
                    "accent": "#ffffff",
                    "text": "#f4f4f5",
                },
            ),
            desktop_layout=DesktopLayout(
                id="nothing_inspired_layout",
                name="Nothing Floating Blueprint",
                description="Top status panel with floating centered bottom dock",
                top_panel=PanelConfig(
                    position="top",
                    thickness=30,
                    visibility="always_visible",
                    applets=["kickoff", "appmenu", "digitalclock", "systemtray"],
                ),
                dock=PanelConfig(
                    position="bottom",
                    thickness=52,
                    icon_size=44,
                    visibility="dodge_windows",
                    is_dock=True,
                    applets=["icontasks"],
                ),
                show_widgets=True,
            ),
            simulated_features={
                "wallpaper": "Nothing Dot Matrix Dark",
                "font_family": "NDOT 57 / Inter 10pt",
                "widget_simulation": "Typographic desktop clock is simulated; install modernclock applet for real Plasma placement.",
            },
        ),
        SetupProfile(
            id="arch_minimalist",
            name="Arch Minimalist",
            tagline="Distraction-free charcoal and monochrome with subtle Arch cyan details.",
            description="Ultralight, sharp aesthetics designed for maximum screen real estate and low resource overhead on integrated graphics.",
            author="PlasmaForge Community",
            version="1.2",
            category="Minimal",
            tags=["Arch", "Minimal", "Lightweight", "Fast"],
            color_scheme=ColorSchemeSpec(
                scheme_id="BreezeClassic",
                name="Arch Cyan Dark",
                preview_colors={
                    "bg": "#121417",
                    "surface": "#1c1f24",
                    "accent": "#1793d1",
                    "text": "#f5f5f5",
                },
            ),
            desktop_layout=DesktopLayout(
                id="arch_minimalist_layout",
                name="Arch Compact Taskbar",
                description="Single compact bottom taskbar",
                top_panel=PanelConfig(position="none", thickness=32),
                dock=PanelConfig(
                    position="bottom",
                    thickness=36,
                    icon_size=30,
                    visibility="always_visible",
                    is_dock=False,
                    applets=["kickoff", "icontasks", "systemtray", "digitalclock"],
                ),
                show_widgets=False,
            ),
            simulated_features={
                "wallpaper": "Arch Charcoal Carbon",
                "font_family": "Inter 10pt",
                "widget_simulation": "Preview simulation only; fonts and wallpapers require manual setup.",
            },
        ),
        SetupProfile(
            id="paper_umber",
            name="Paper & Umber Dark",
            tagline="Low-strain warm umber palette designed for prolonged reading.",
            description="Soft earthy background tones replacing harsh blue-tinted grays. Ideal for nighttime drafting and documentation.",
            author="PlasmaForge Studio",
            version="1.0",
            category="Productivity",
            tags=["Warm", "Reading", "Low-Contrast", "Productivity"],
            color_scheme=ColorSchemeSpec(
                scheme_id="BreezeDark",
                name="Warm Amber Dark",
                preview_colors={
                    "bg": "#1e1d1b",
                    "surface": "#2a2825",
                    "accent": "#d97706",
                    "text": "#e7e5e4",
                },
            ),
            desktop_layout=DesktopLayout(
                id="paper_umber_layout",
                name="Warm Standard Panel",
                description="Standard bottom panel arrangement",
                top_panel=PanelConfig(position="none", thickness=32),
                dock=PanelConfig(
                    position="bottom",
                    thickness=44,
                    icon_size=36,
                    visibility="always_visible",
                    is_dock=False,
                    applets=["kickoff", "taskmanager", "systemtray", "digitalclock"],
                ),
                show_widgets=False,
            ),
            simulated_features={
                "wallpaper": "Warm Paper Texture Dark",
                "font_family": "Inter 10pt",
                "widget_simulation": "Preview simulation only; fonts and wallpapers require manual setup.",
            },
        ),
    ]


class ProfileManager:
    """Handles discovery, importing, exporting, and safe storage of setup profiles."""

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self.storage_dir = storage_dir or (
            Path.home() / ".local" / "share" / "plasmaforge" / "profiles"
        )
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._curated_profiles = get_curated_profiles()

    def list_profiles(self) -> List[SetupProfile]:
        """Return combined list of curated profiles and valid user-imported profiles."""
        profiles: List[SetupProfile] = list(self._curated_profiles)
        existing_ids = {p.id for p in profiles}

        if self.storage_dir.is_dir():
            for p in sorted(self.storage_dir.glob("*.json")):
                try:
                    # Guard oversized files
                    if p.stat().st_size > MAX_PROFILE_FILE_SIZE_BYTES:
                        continue
                    text = p.read_text(encoding="utf-8")
                    data = json.loads(text)
                    profile = SetupProfile.from_dict(data, is_imported=True)
                    if profile.id not in existing_ids:
                        profiles.append(profile)
                        existing_ids.add(profile.id)
                except Exception:
                    continue

        return profiles

    def get_profile(self, profile_id: str) -> Optional[SetupProfile]:
        """Find a profile by ID."""
        for p in self.list_profiles():
            if p.id == profile_id:
                return p
        return None

    def import_profile_json(self, json_str: str) -> tuple[bool, str, Optional[SetupProfile]]:
        """Validate and safely store a JSON profile without mutating KDE configuration."""
        if not json_str or not json_str.strip():
            return False, "Cannot import empty profile data.", None

        if len(json_str.encode("utf-8")) > MAX_PROFILE_FILE_SIZE_BYTES:
            return (
                False,
                f"Profile file size exceeds maximum limit ({MAX_PROFILE_FILE_SIZE_BYTES // 1024} KB).",
                None,
            )

        try:
            data = json.loads(json_str)
        except Exception as e:
            return False, f"Malformed JSON: {e}", None

        if not isinstance(data, dict):
            return False, "Profile root must be a JSON object.", None

        try:
            profile = SetupProfile.from_dict(data, is_imported=True)
        except ProfileValidationError as e:
            return False, str(e), None
        except Exception as e:
            return False, f"Invalid profile data: {e}", None

        # Handle duplicate IDs
        existing_ids = {p.id for p in self.list_profiles()}
        if profile.id in existing_ids:
            counter = 1
            base_id = profile.id
            while f"{base_id}_{counter}" in existing_ids:
                counter += 1
            profile.id = f"{base_id}_{counter}"
            profile.name = f"{profile.name} (Imported)"

        # Save to storage directory
        target_path = self.storage_dir / f"{profile.id}.json"
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            target_path.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
        except Exception as e:
            return False, f"Failed to save profile to disk: {e}", None

        return True, f"Successfully imported profile '{profile.name}'.", profile

    def import_profile_file(self, file_path: Path) -> tuple[bool, str, Optional[SetupProfile]]:
        """Import a profile from a filesystem path."""
        p = Path(file_path)
        if not p.is_file():
            return False, f"Profile file not found: {p}", None

        try:
            size = p.stat().st_size
            if size > MAX_PROFILE_FILE_SIZE_BYTES:
                return (
                    False,
                    f"Profile file size ({size // 1024} KB) exceeds maximum limit ({MAX_PROFILE_FILE_SIZE_BYTES // 1024} KB).",
                    None,
                )
            text = p.read_text(encoding="utf-8", errors="replace")
            return self.import_profile_json(text)
        except Exception as e:
            return False, f"Failed to read profile file: {e}", None

    def export_profile(self, profile_id: str, dest_path: Path) -> tuple[bool, str]:
        """Export a profile to a destination JSON file."""
        profile = self.get_profile(profile_id)
        if not profile:
            return False, f"Profile '{profile_id}' not found."

        dest = Path(dest_path)
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
            return True, f"Successfully exported profile '{profile.name}' to {dest.name}."
        except Exception as e:
            return False, f"Failed to export profile: {e}"
