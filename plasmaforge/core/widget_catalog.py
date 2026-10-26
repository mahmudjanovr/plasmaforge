"""Installed KDE Plasma widget catalog discovery and metadata inspection service.

Discovers real installed Plasma 6 widgets across user and system package directories.
Guarantees:
1. Purely read-only: zero configuration writes or package modifications.
2. Honest discovery: strictly identifies installed widgets from verified filesystem
   locations. Never presents an uninstalled catalog item as installed.
3. Resilient parsing: gracefully handles missing metadata, malformed JSON,
   and legacy desktop entry formats.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# Standard category mappings for built-in Plasma applets
KNOWN_PLUGIN_METADATA: Dict[str, Dict[str, str]] = {
    "org.kde.plasma.kickoff": {
        "name": "Application Launcher",
        "description": "Launcher menu for applications, system settings, and power actions.",
        "category": "Application Launchers",
        "icon": "start-here-kde",
    },
    "org.kde.plasma.kicker": {
        "name": "Application Menu",
        "description": "Classic hierarchical application menu.",
        "category": "Application Launchers",
        "icon": "start-here-kde",
    },
    "org.kde.plasma.appmenu": {
        "name": "Global Menu",
        "description": "Displays application menu bar in the panel.",
        "category": "Application Launchers",
        "icon": "application-menu",
    },
    "org.kde.plasma.digitalclock": {
        "name": "Digital Clock",
        "description": "Time and date display with calendar integration.",
        "category": "Date and Time",
        "icon": "preferences-system-time",
    },
    "org.kde.plasma.analogclock": {
        "name": "Analog Clock",
        "description": "Traditional analog clock face.",
        "category": "Date and Time",
        "icon": "clock",
    },
    "org.kde.plasma.calendar": {
        "name": "Calendar",
        "description": "Interactive month calendar and event list.",
        "category": "Date and Time",
        "icon": "view-calendar",
    },
    "org.kde.plasma.systemtray": {
        "name": "System Tray",
        "description": "Access to status indicators and background applications.",
        "category": "System Information",
        "icon": "preferences-desktop-notification",
    },
    "org.kde.plasma.icontasks": {
        "name": "Icons-Only Task Manager",
        "description": "Dock-style application launcher and window switcher using icons.",
        "category": "Windows and Tasks",
        "icon": "preferences-system-windows",
    },
    "org.kde.plasma.taskmanager": {
        "name": "Task Manager",
        "description": "Conventional task bar displaying window titles.",
        "category": "Windows and Tasks",
        "icon": "preferences-system-windows",
    },
    "org.kde.plasma.pager": {
        "name": "Pager",
        "description": "Virtual desktop switcher.",
        "category": "Windows and Tasks",
        "icon": "user-desktop",
    },
    "org.kde.plasma.showdesktop": {
        "name": "Peek at Desktop",
        "description": "Minimizes or peeks through windows to show the desktop.",
        "category": "Windows and Tasks",
        "icon": "user-desktop",
    },
    "org.kde.plasma.minimizeall": {
        "name": "Minimize All Windows",
        "description": "Quickly minimizes all active windows.",
        "category": "Windows and Tasks",
        "icon": "show-desktop",
    },
    "org.kde.plasma.panelspacer": {
        "name": "Panel Spacer",
        "description": "Flexible or fixed blank spacing between panel applets.",
        "category": "Windows and Tasks",
        "icon": "distribute-horizontal-margin",
    },
    "org.kde.plasma.marginsseparator": {
        "name": "Margins Separator",
        "description": "Subtle visual separator matching panel theme margins.",
        "category": "Windows and Tasks",
        "icon": "format-line-spacing-normal",
    },
    "org.kde.plasma.volume": {
        "name": "Audio Volume",
        "description": "Volume control and audio stream mixer.",
        "category": "Multimedia",
        "icon": "audio-volume-high",
    },
    "org.kde.plasma.mediacontroller": {
        "name": "Media Controller",
        "description": "Controls for active audio and video playback.",
        "category": "Multimedia",
        "icon": "media-playback-start",
    },
    "org.kde.plasma.battery": {
        "name": "Battery and Brightness",
        "description": "Power profile, battery charge, and screen brightness indicator.",
        "category": "System Information",
        "icon": "battery-charging",
    },
    "org.kde.plasma.brightness": {
        "name": "Brightness",
        "description": "Display backlight brightness adjustment.",
        "category": "System Information",
        "icon": "display-brightness",
    },
    "org.kde.plasma.networkmanagement": {
        "name": "Networks",
        "description": "Wi-Fi, Ethernet, and VPN connection manager.",
        "category": "System Information",
        "icon": "network-wireless-connected-100",
    },
    "org.kde.plasma.notifications": {
        "name": "Notifications",
        "description": "Notification history and active alerts.",
        "category": "System Information",
        "icon": "preferences-desktop-notification",
    },
    "org.kde.plasma.clipboard": {
        "name": "Clipboard",
        "description": "Clipboard history and snippet manager.",
        "category": "Utilities",
        "icon": "klipper",
    },
    "org.kde.plasma.devicenotifier": {
        "name": "Disks & Devices",
        "description": "Removable media and storage device notifier.",
        "category": "Utilities",
        "icon": "drive-removable-media",
    },
    "org.kde.plasma.trash": {
        "name": "Trash",
        "description": "Recycle bin shortcut and capacity indicator.",
        "category": "Utilities",
        "icon": "user-trash",
    },
    "org.kde.plasma.systemmonitor": {
        "name": "System Monitor",
        "description": "Charts and gauges for processor, RAM, and network usage.",
        "category": "System Information",
        "icon": "utilities-system-monitor",
    },
    "org.kde.plasma.systemmonitor.cpu": {
        "name": "CPU Usage",
        "description": "Real-time CPU load sensor graph.",
        "category": "System Information",
        "icon": "cpu",
    },
    "org.kde.plasma.systemmonitor.memory": {
        "name": "Memory Usage",
        "description": "Real-time physical and swap memory usage.",
        "category": "System Information",
        "icon": "ram",
    },
    "org.kde.plasma.systemmonitor.net": {
        "name": "Network Speed",
        "description": "Real-time network transfer rate graph.",
        "category": "System Information",
        "icon": "network-workgroup",
    },
    "org.kde.plasma.lock_logout": {
        "name": "Lock/Logout",
        "description": "Session locking, shutdown, and reboot shortcuts.",
        "category": "System Information",
        "icon": "system-lock-screen",
    },
}

# Panels-only applets (not suitable as floating desktop widgets)
PANEL_ONLY_PLUGINS = {
    "org.kde.plasma.panelspacer",
    "org.kde.plasma.marginsseparator",
    "org.kde.plasma.appmenu",
}

# Desktop-only containments / widgets
DESKTOP_ONLY_PLUGINS = {
    "org.kde.plasma.folder",
    "org.kde.desktopcontainment",
}


@dataclass
class InstalledWidgetInfo:
    """Detailed metadata for a verified installed KDE Plasma widget."""

    plugin_id: str
    name: str
    description: str = ""
    category: str = "Utilities"
    icon: str = "plasma"
    author: str = ""
    version: str = "1.0"
    source: str = "system_package"  # "system_package" or "user_installed"
    path: str = ""
    suitable_for: List[str] = field(default_factory=lambda: ["panel", "desktop"])
    placement_supported: bool = True
    is_installed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InstalledWidgetInfo:
        return cls(
            plugin_id=str(data.get("plugin_id", "")),
            name=str(data.get("name", "Unknown Widget")),
            description=str(data.get("description", "")),
            category=str(data.get("category", "Utilities")),
            icon=str(data.get("icon", "plasma")),
            author=str(data.get("author", "")),
            version=str(data.get("version", "1.0")),
            source=str(data.get("source", "system_package")),
            path=str(data.get("path", "")),
            suitable_for=list(data.get("suitable_for", ["panel", "desktop"])),
            placement_supported=bool(data.get("placement_supported", True)),
            is_installed=bool(data.get("is_installed", True)),
        )


class WidgetCatalogService:
    """Discovers and catalogs real installed KDE Plasma 6 widgets."""

    def __init__(
        self,
        user_plasmoids_dir: Optional[Path] = None,
        system_plasmoids_dir: Optional[Path] = None,
        system_qt_plugins_dir: Optional[Path] = None,
        system_applets_dir: Optional[Path] = None,
    ) -> None:
        self._is_default_paths = (
            user_plasmoids_dir is None
            and system_plasmoids_dir is None
            and system_qt_plugins_dir is None
            and system_applets_dir is None
        )
        self.user_plasmoids_dir = user_plasmoids_dir or (Path.home() / ".local" / "share" / "plasma" / "plasmoids")
        self.system_plasmoids_dir = system_plasmoids_dir or Path("/usr/share/plasma/plasmoids")
        self.system_qt_plugins_dir = system_applets_dir or system_qt_plugins_dir or Path("/usr/lib/qt6/plugins/plasma/applets")

        self._cached_widgets: Optional[List[InstalledWidgetInfo]] = None

    def get_installed_widgets(self, refresh: bool = False, force_refresh: bool = False) -> List[InstalledWidgetInfo]:
        """Discover all verified installed widgets across user and system paths."""
        do_refresh = refresh or force_refresh
        if self._cached_widgets is not None and not do_refresh:
            return self._cached_widgets

        widgets_by_id: Dict[str, InstalledWidgetInfo] = {}

        # 1. User plasmoids in ~/.local/share/plasma/plasmoids
        if self.user_plasmoids_dir.is_dir():
            for entry in self.user_plasmoids_dir.iterdir():
                if entry.is_dir() and not entry.name.startswith("."):
                    info = self._inspect_plasmoid_directory(entry, is_user=True)
                    if info:
                        widgets_by_id[info.plugin_id] = info

        # 2. System QML plasmoids in /usr/share/plasma/plasmoids
        if self.system_plasmoids_dir.is_dir():
            for entry in self.system_plasmoids_dir.iterdir():
                if entry.is_dir() and not entry.name.startswith("."):
                    info = self._inspect_plasmoid_directory(entry, is_user=False)
                    if info and info.plugin_id not in widgets_by_id:
                        widgets_by_id[info.plugin_id] = info

        # 3. System C++ binary applet plugins in /usr/lib/qt6/plugins/plasma/applets
        if self.system_qt_plugins_dir.is_dir():
            for entry in self.system_qt_plugins_dir.iterdir():
                if entry.is_file() and entry.name.endswith(".so"):
                    plugin_id = entry.name[:-3]
                    if (plugin_id.startswith("org.kde.") or not self._is_default_paths) and plugin_id not in widgets_by_id:
                        info = self._inspect_binary_plugin(entry, plugin_id)
                        if info:
                            widgets_by_id[info.plugin_id] = info

        # Also check /usr/lib64/qt6/plugins/plasma/applets if using default paths
        if self._is_default_paths:
            alt_qt_dir = Path("/usr/lib64/qt6/plugins/plasma/applets")
            if alt_qt_dir.is_dir() and alt_qt_dir != self.system_qt_plugins_dir:
                for entry in alt_qt_dir.iterdir():
                    if entry.is_file() and entry.name.endswith(".so"):
                        plugin_id = entry.name[:-3]
                        if plugin_id.startswith("org.kde.") and plugin_id not in widgets_by_id:
                            info = self._inspect_binary_plugin(entry, plugin_id)
                            if info:
                                widgets_by_id[info.plugin_id] = info

        # Sort alphabetically by display name
        result = sorted(widgets_by_id.values(), key=lambda w: w.name.lower())
        self._cached_widgets = result
        return result

    def find_widget(self, plugin_id: str) -> Optional[InstalledWidgetInfo]:
        """Find a single installed widget by plugin ID."""
        for w in self.get_installed_widgets():
            if w.plugin_id == plugin_id or w.plugin_id == f"org.kde.plasma.{plugin_id}":
                return w
        return None

    def is_widget_installed(self, plugin_id: str) -> bool:
        """Check whether a widget plugin is installed on the host system."""
        return self.find_widget(plugin_id) is not None

    def search_widgets(
        self,
        query: str = "",
        category: Optional[str] = None,
        target_suitability: Optional[str] = None,
        target: Optional[str] = None,
        widgets: Optional[List[InstalledWidgetInfo]] = None,
    ) -> List[InstalledWidgetInfo]:
        """Filter installed widgets by text query, category, and target (panel/desktop)."""
        widget_list = widgets if widgets is not None else self.get_installed_widgets()
        q = query.strip().lower()
        effective_target = target or target_suitability

        filtered: List[InstalledWidgetInfo] = []
        for w in widget_list:
            if q and (q not in w.name.lower() and q not in w.plugin_id.lower() and q not in w.description.lower()):
                continue

            if category and category != "All" and w.category.lower() != category.lower():
                continue

            if effective_target and effective_target != "All":
                if effective_target.lower() not in [s.lower() for s in w.suitable_for]:
                    continue

            filtered.append(w)

        return filtered

    def get_categories(self) -> List[str]:
        """Return unique sorted list of discovered widget categories."""
        cats = {w.category for w in self.get_installed_widgets() if w.category}
        return sorted(cats)

    # --------------------------------------------------------------------------
    # Private Parsers
    # --------------------------------------------------------------------------

    def _inspect_plasmoid_directory(self, dir_path: Path, is_user: bool) -> Optional[InstalledWidgetInfo]:
        """Inspect a plasmoid folder containing metadata.json or metadata.desktop."""
        meta_json = dir_path / "metadata.json"
        meta_desktop = dir_path / "metadata.desktop"

        plugin_id = dir_path.name
        name = self._beautify_plugin_name(plugin_id)
        description = ""
        category = "Utilities"
        icon = "plasma"
        author = ""
        version = "1.0"

        # Check metadata.json (standard in Plasma 5/6)
        if meta_json.is_file():
            try:
                data = json.loads(meta_json.read_text(encoding="utf-8", errors="replace"))
                kplugin = data.get("KPlugin", {})
                if isinstance(kplugin, dict):
                    plugin_id = str(kplugin.get("Id") or plugin_id)
                    name = str(kplugin.get("Name") or name)
                    description = str(kplugin.get("Description") or "")
                    category = str(kplugin.get("Category") or category)
                    icon = str(kplugin.get("Icon") or icon)
                    version = str(kplugin.get("Version") or version)

                    authors_data = kplugin.get("Authors", [])
                    if isinstance(authors_data, list) and authors_data:
                        first_author = authors_data[0]
                        if isinstance(first_author, dict):
                            author = str(first_author.get("Name", ""))
                        elif isinstance(first_author, str):
                            author = first_author
            except Exception as e:
                logger.warning("Error parsing %s: %s", meta_json, e)

        # Fallback to metadata.desktop if metadata.json was absent or empty
        elif meta_desktop.is_file():
            try:
                text = meta_desktop.read_text(encoding="utf-8", errors="replace")
                for line in text.splitlines():
                    if line.startswith("Name=") and name == self._beautify_plugin_name(plugin_id):
                        name = line.split("=", 1)[1].strip()
                    elif line.startswith("Comment="):
                        description = line.split("=", 1)[1].strip()
                    elif line.startswith("X-KDE-PluginInfo-Category="):
                        category = line.split("=", 1)[1].strip()
                    elif line.startswith("Icon="):
                        icon = line.split("=", 1)[1].strip()
                    elif line.startswith("X-KDE-PluginInfo-Author="):
                        author = line.split("=", 1)[1].strip()
                    elif line.startswith("X-KDE-PluginInfo-Version="):
                        version = line.split("=", 1)[1].strip()
                    elif line.startswith("X-KDE-PluginInfo-Name="):
                        plugin_id = line.split("=", 1)[1].strip()
            except Exception as e:
                logger.warning("Error parsing %s: %s", meta_desktop, e)

        # Fallback known metadata if available
        if plugin_id in KNOWN_PLUGIN_METADATA:
            known = KNOWN_PLUGIN_METADATA[plugin_id]
            if not description:
                description = known["description"]
            if category == "Utilities" and "category" in known:
                category = known["category"]
            if icon == "plasma" and "icon" in known:
                icon = known["icon"]
            if name == self._beautify_plugin_name(plugin_id):
                name = known["name"]

        # Determine suitability
        suitable_for = ["panel", "desktop"]
        if plugin_id in PANEL_ONLY_PLUGINS:
            suitable_for = ["panel"]
        elif plugin_id in DESKTOP_ONLY_PLUGINS:
            suitable_for = ["desktop"]

        return InstalledWidgetInfo(
            plugin_id=plugin_id,
            name=name,
            description=description,
            category=category,
            icon=icon,
            author=author,
            version=version,
            source="user_installed" if is_user else "system_package",
            path=str(dir_path),
            suitable_for=suitable_for,
            placement_supported=True,
            is_installed=True,
        )

    def _inspect_binary_plugin(self, so_path: Path, plugin_id: str) -> Optional[InstalledWidgetInfo]:
        """Inspect a binary C++ Qt6 Plasma applet plugin (.so)."""
        name = self._beautify_plugin_name(plugin_id)
        description = ""
        category = "Utilities"
        icon = "plasma"

        if plugin_id in KNOWN_PLUGIN_METADATA:
            known = KNOWN_PLUGIN_METADATA[plugin_id]
            name = known.get("name", name)
            description = known.get("description", "")
            category = known.get("category", "Utilities")
            icon = known.get("icon", "plasma")

        suitable_for = ["panel", "desktop"]
        if plugin_id in PANEL_ONLY_PLUGINS:
            suitable_for = ["panel"]
        elif plugin_id in DESKTOP_ONLY_PLUGINS:
            suitable_for = ["desktop"]

        return InstalledWidgetInfo(
            plugin_id=plugin_id,
            name=name,
            description=description,
            category=category,
            icon=icon,
            author="KDE Community",
            version="6.0",
            source="system_package",
            path=str(so_path),
            suitable_for=suitable_for,
            placement_supported=True,
            is_installed=True,
        )

    def _beautify_plugin_name(self, plugin_id: str) -> str:
        """Convert a plugin ID like 'org.kde.plasma.digitalclock' to 'Digital Clock'."""
        short_id = plugin_id.replace("org.kde.plasma.", "").replace("org.kde.", "")
        parts = short_id.replace("_", "-").split("-")
        return " ".join(p.capitalize() for p in parts)
