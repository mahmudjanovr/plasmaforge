"""Safe inspection of KDE Plasma color schemes and desktop styles."""

from __future__ import annotations

import configparser
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional


def _rgb_to_hex(rgb_str: Optional[str], default: str = "#202328") -> str:
    """Convert KDE RGB string (e.g. '32,35,38') to Hex color (e.g. '#202326')."""
    if not rgb_str:
        return default
    parts = [p.strip() for p in rgb_str.split(",")]
    if len(parts) >= 3:
        try:
            r = max(0, min(255, int(parts[0])))
            g = max(0, min(255, int(parts[1])))
            b = max(0, min(255, int(parts[2])))
            return f"#{r:02x}{g:02x}{b:02x}"
        except ValueError:
            pass
    return default


@dataclass
class ColorSchemeInfo:
    """Metadata and palette preview for a KDE color scheme."""

    id: str
    name: str
    file_path: str
    is_user_scheme: bool
    window_bg: str
    window_fg: str
    view_bg: str
    view_fg: str
    selection_bg: str
    selection_fg: str
    button_bg: str
    button_fg: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class PlasmaStyleInfo:
    """Metadata for a KDE Plasma desktop theme / style."""

    id: str
    name: str
    comment: str
    author: str
    path: str
    is_user_style: bool

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class ThemeInspector:
    """Safe, read-only scanner for installed KDE color schemes and Plasma styles."""

    def __init__(self) -> None:
        self.scheme_dirs = [
            Path.home() / ".local" / "share" / "color-schemes",
            Path("/usr/share/color-schemes"),
        ]
        self.plasma_dirs = [
            Path.home() / ".local" / "share" / "plasma" / "desktoptheme",
            Path("/usr/share/plasma/desktoptheme"),
        ]

    def get_color_schemes(self) -> List[ColorSchemeInfo]:
        """Discover and parse installed color schemes."""
        schemes: List[ColorSchemeInfo] = []
        seen_names = set()

        for directory in self.scheme_dirs:
            if not directory.is_dir():
                continue
            is_user = directory.resolve().is_relative_to(Path.home().resolve())

            for path in sorted(directory.glob("*.colors")):
                try:
                    cfg = configparser.ConfigParser(interpolation=None)
                    cfg.optionxform = str
                    cfg.read(path, encoding="utf-8")

                    name = path.stem
                    if cfg.has_section("General"):
                        name = cfg.get("General", "Name", fallback=path.stem)

                    if name in seen_names:
                        continue
                    seen_names.add(name)

                    win_bg = _rgb_to_hex(
                        cfg.get("Colors:Window", "BackgroundNormal", fallback=None),
                        "#202328",
                    )
                    win_fg = _rgb_to_hex(
                        cfg.get("Colors:Window", "ForegroundNormal", fallback=None),
                        "#f0f2f5",
                    )
                    view_bg = _rgb_to_hex(
                        cfg.get("Colors:View", "BackgroundNormal", fallback=None),
                        "#181a1f",
                    )
                    view_fg = _rgb_to_hex(
                        cfg.get("Colors:View", "ForegroundNormal", fallback=None),
                        "#f0f2f5",
                    )
                    sel_bg = _rgb_to_hex(
                        cfg.get("Colors:Selection", "BackgroundNormal", fallback=None),
                        "#14b8a6",
                    )
                    sel_fg = _rgb_to_hex(
                        cfg.get("Colors:Selection", "ForegroundNormal", fallback=None),
                        "#ffffff",
                    )
                    btn_bg = _rgb_to_hex(
                        cfg.get("Colors:Button", "BackgroundNormal", fallback=None),
                        "#2d3139",
                    )
                    btn_fg = _rgb_to_hex(
                        cfg.get("Colors:Button", "ForegroundNormal", fallback=None),
                        "#e0e2e6",
                    )

                    schemes.append(
                        ColorSchemeInfo(
                            id=path.stem,
                            name=name,
                            file_path=str(path),
                            is_user_scheme=is_user,
                            window_bg=win_bg,
                            window_fg=win_fg,
                            view_bg=view_bg,
                            view_fg=view_fg,
                            selection_bg=sel_bg,
                            selection_fg=sel_fg,
                            button_bg=btn_bg,
                            button_fg=btn_fg,
                        )
                    )
                except Exception:
                    continue

        return schemes

    def get_plasma_styles(self) -> List[PlasmaStyleInfo]:
        """Discover installed Plasma desktop styles."""
        styles: List[PlasmaStyleInfo] = []
        seen_ids = set()

        for directory in self.plasma_dirs:
            if not directory.is_dir():
                continue
            is_user = directory.resolve().is_relative_to(Path.home().resolve())

            for sub in sorted(directory.iterdir()):
                if not sub.is_dir() or sub.name in seen_ids:
                    continue

                theme_id = sub.name
                name = theme_id.capitalize()
                comment = "Plasma Desktop Theme"
                author = "KDE Community"

                meta_json = sub / "metadata.json"
                if meta_json.is_file():
                    try:
                        with open(meta_json, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            kplugin = data.get("KPlugin", {})
                            name = kplugin.get("Name", name)
                            comment = kplugin.get("Description", comment)
                            authors = kplugin.get("Authors", [])
                            if authors and isinstance(authors, list):
                                author = authors[0].get("Name", author)
                    except Exception:
                        pass
                else:
                    meta_desk = sub / "metadata.desktop"
                    if meta_desk.is_file():
                        try:
                            cfg = configparser.ConfigParser(interpolation=None)
                            cfg.optionxform = str
                            cfg.read(meta_desk, encoding="utf-8")
                            sec = (
                                "Desktop Entry"
                                if cfg.has_section("Desktop Entry")
                                else cfg.sections()[0]
                            )
                            name = cfg.get(sec, "Name", fallback=name)
                            comment = cfg.get(sec, "Comment", fallback=comment)
                            author = cfg.get(
                                sec, "X-KDE-PluginInfo-Author", fallback=author
                            )
                        except Exception:
                            pass

                seen_ids.add(theme_id)
                styles.append(
                    PlasmaStyleInfo(
                        id=theme_id,
                        name=name,
                        comment=comment,
                        author=author,
                        path=str(sub),
                        is_user_style=is_user,
                    )
                )

        return styles
