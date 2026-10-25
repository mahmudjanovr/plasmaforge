"""Curated desktop presets and recipes for the Setup Gallery."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List

from plasmaforge.core.adapter_boundary import ConfigChange, ConfigChangeSet


@dataclass
class PresetBundle:
    """Preset customization recipe for KDE Plasma 6."""

    id: str
    title: str
    tagline: str
    description: str
    author: str
    version: str
    tags: List[str]
    preview_colors: Dict[str, str]
    components: Dict[str, str]
    changes: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_changeset(self) -> ConfigChangeSet:
        """Convert preset into a validated ConfigChangeSet for dry-run preview."""
        change_objects = [
            ConfigChange(
                file_identifier=c["file"],
                group=c["group"],
                key=c["key"],
                new_value=c["value"],
                reason=f"Apply preset: {self.title}",
            )
            for c in self.changes
        ]
        return ConfigChangeSet(
            name=self.title,
            description=self.description,
            changes=change_objects,
        )


CURATED_PRESETS: List[PresetBundle] = [
    PresetBundle(
        id="obsidian-teal",
        title="Obsidian Teal Studio",
        tagline="Slate dark base with restrained electric teal highlights and crisp typography.",
        description="Engineered for long development sessions on KDE Plasma 6. Features deep neutral backgrounds, low glare, and high legibility.",
        author="PlasmaForge Core",
        version="1.0",
        tags=["KDE 6", "Dark", "Teal", "Productivity"],
        preview_colors={
            "bg": "#181a1f",
            "surface": "#22252c",
            "accent": "#14b8a6",
            "text": "#eff0f1",
        },
        components={
            "Color Scheme": "Breeze Dark",
            "Plasma Style": "breeze-dark",
            "Font": "Inter 10pt",
            "Monospace": "JetBrains Mono 10pt",
            "Panel Layout": "Floating Bottom Bar (44px)",
        },
        changes=[
            {
                "file": "kdeglobals",
                "group": "KDE",
                "key": "LookAndFeelPackage",
                "value": "org.kde.breezedark.desktop",
            },
            {
                "file": "kdeglobals",
                "group": "Colors:Selection",
                "key": "BackgroundNormal",
                "value": "20,184,166",
            },
            {
                "file": "kdeglobals",
                "group": "General",
                "key": "font",
                "value": "Inter,10,-1,5,400,0,0,0,0,0,0,0,0,0,0,1",
            },
        ],
    ),
    PresetBundle(
        id="nordic-aurora",
        title="Nordic Horizon",
        tagline="Cool arctic slate with soft cyan and polar blue accents.",
        description="Clean Nordic palette adapted for native Qt Quick and Plasma 6. Provides balanced contrast with smooth visual hierarchy.",
        author="PlasmaForge Core",
        version="1.0",
        tags=["Nord", "Clean", "Wayland", "Developer"],
        preview_colors={
            "bg": "#242933",
            "surface": "#2e3440",
            "accent": "#88c0d0",
            "text": "#eceff4",
        },
        components={
            "Color Scheme": "Nordic Dark",
            "Plasma Style": "default",
            "Font": "Inter 10pt",
            "Monospace": "JetBrains Mono 10pt",
            "Panel Layout": "Top Status Bar + Auto-Hide Dock",
        },
        changes=[
            {
                "file": "kdeglobals",
                "group": "KDE",
                "key": "LookAndFeelPackage",
                "value": "org.kde.breezedark.desktop",
            },
            {
                "file": "kdeglobals",
                "group": "Colors:Selection",
                "key": "BackgroundNormal",
                "value": "136,192,208",
            },
        ],
    ),
    PresetBundle(
        id="arch-minimalist",
        title="Arch Minimalist",
        tagline="Distraction-free charcoal and monochrome with subtle Arch cyan details.",
        description="Ultralight, sharp aesthetics designed for maximum screen real estate and low resource overhead on integrated graphics.",
        author="PlasmaForge Community",
        version="1.2",
        tags=["Arch", "Minimal", "Lightweight", "Fast"],
        preview_colors={
            "bg": "#121417",
            "surface": "#1c1f24",
            "accent": "#1793d1",
            "text": "#f5f5f5",
        },
        components={
            "Color Scheme": "Breeze Classic",
            "Plasma Style": "breeze-dark",
            "Font": "Inter 10pt",
            "Monospace": "JetBrains Mono 10pt",
            "Panel Layout": "Compact Bottom Panel (36px)",
        },
        changes=[
            {
                "file": "kdeglobals",
                "group": "KDE",
                "key": "LookAndFeelPackage",
                "value": "org.kde.breeze.desktop",
            },
            {
                "file": "kdeglobals",
                "group": "Colors:Selection",
                "key": "BackgroundNormal",
                "value": "23,147,209",
            },
        ],
    ),
    PresetBundle(
        id="studio-warm",
        title="Paper & Umber Dark",
        tagline="Low-strain warm umber palette designed for prolonged reading.",
        description="Soft earthy background tones replacing harsh blue-tinted grays. Ideal for nighttime drafting and documentation.",
        author="PlasmaForge Studio",
        version="1.0",
        tags=["Warm", "Reading", "Low-Contrast"],
        preview_colors={
            "bg": "#1e1d1b",
            "surface": "#2a2825",
            "accent": "#d97706",
            "text": "#e7e5e4",
        },
        components={
            "Color Scheme": "Breeze Dark",
            "Plasma Style": "default",
            "Font": "Inter 10pt",
            "Monospace": "JetBrains Mono 10pt",
            "Panel Layout": "Standard Plasma 6 Panel",
        },
        changes=[
            {
                "file": "kdeglobals",
                "group": "KDE",
                "key": "LookAndFeelPackage",
                "value": "org.kde.breezedark.desktop",
            },
            {
                "file": "kdeglobals",
                "group": "Colors:Selection",
                "key": "BackgroundNormal",
                "value": "217,119,6",
            },
        ],
    ),
]


def get_all_presets() -> List[PresetBundle]:
    """Return all available setup gallery presets."""
    return list(CURATED_PRESETS)
