"""Comprehensive tests for live KDE Plasma desktop inspection, environment detection, and change analysis."""

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from plasmaforge.controllers.desktop_controller import DesktopController
from plasmaforge.core.desktop_inspector import (
    DesktopChangeAnalyzer,
    DesktopEnvironmentDetector,
    DesktopLayoutInspector,
    DetectedAppletInfo,
    DetectedPanelInfo,
    DisplayOutputInfo,
    LiveDesktopState,
    ProposedChange,
)
from plasmaforge.core.desktop_layout import DesktopLayout, PanelConfig


# ==============================================================================
# Sample Fixture Data
# ==============================================================================

SAMPLE_KSCREEN_JSON = json.dumps({
    "outputs": [
        {
            "name": "eDP-1",
            "connected": True,
            "enabled": True,
            "primary": True,
            "scale": 1.0,
            "currentMode": {
                "size": {"width": 1920, "height": 1080},
                "refreshRate": 60.0,
            },
        },
        {
            "name": "DP-1",
            "connected": False,
            "enabled": False,
            "primary": False,
            "scale": 1.0,
            "currentMode": None,
        },
    ]
})

SAMPLE_DBUS_LAYOUT_JS = """
var layout = {
    "desktops": [
        {
            "applets": [
                {
                    "geometry": {"height": 150, "width": 250, "x": 100, "y": 100},
                    "plugin": "com.github.prayag2.modernclock",
                    "title": "Modern Clock"
                }
            ],
            "config": {
                "/": {"wallpaperplugin": "org.kde.image"},
                "/Wallpaper/org.kde.image/General": {"Image": "/home/user/Pictures/wallpaper.jpg"}
            }
        }
    ],
    "panels": [
        {
            "alignment": "center",
            "applets": [
                {"geometry": {"height": 38, "width": 38, "x": 0, "y": 0}, "plugin": "org.kde.plasma.kickoff", "title": "Application Launcher"},
                {"geometry": {"height": 38, "width": 120, "x": 40, "y": 0}, "plugin": "org.kde.plasma.digitalclock", "title": "Digital Clock"}
            ],
            "floating": false,
            "height": 40,
            "hiding": "normal",
            "length": 1920,
            "location": "top",
            "maximumLength": 1920,
            "minimumLength": 1920,
            "offset": 0
        },
        {
            "alignment": "center",
            "applets": [
                {"geometry": {"height": 52, "width": 300, "x": 0, "y": 0}, "plugin": "org.kde.plasma.icontasks", "title": "Icons-only Task Manager"}
            ],
            "floating": true,
            "height": 56,
            "hiding": "autohide",
            "length": 800,
            "location": "bottom",
            "maximumLength": 1200,
            "minimumLength": 400,
            "offset": 560
        }
    ]
};

plasma.loadSerializedLayout(layout);
"""

SAMPLE_APPLETRC_CONTENT = """[Containments][47]
activityId=
formfactor=2
immutability=1
lastScreen=0
location=3
plugin=org.kde.panel
wallpaperplugin=org.kde.image

[Containments][47][Applets][48]
immutability=1
plugin=org.kde.plasma.kickoff

[Containments][47][Applets][49]
immutability=1
plugin=org.kde.plasma.digitalclock

[Containments][47][ConfigDialog]
DialogHeight=40
DialogWidth=1920

[Containments][61]
activityId=
formfactor=2
immutability=1
lastScreen=0
location=4
plugin=org.kde.panel
wallpaperplugin=org.kde.image

[Containments][61][Applets][62]
immutability=1
plugin=org.kde.plasma.icontasks

[Containments][61][ConfigDialog]
DialogHeight=56
DialogWidth=800

[Containments][46]
activityId=
formfactor=0
immutability=1
lastScreen=0
location=0
plugin=org.kde.plasma.folder
wallpaperplugin=org.kde.image

[Containments][46][Applets][67]
immutability=1
plugin=com.github.prayag2.modernclock

[Containments][46][Wallpaper][org.kde.image][General]
Image=/home/user/Pictures/wallpaper.jpg
"""


# ==============================================================================
# Environment Detector Tests
# ==============================================================================

def test_environment_detector_kscreen_parsing():
    """Verify parsing of kscreen-doctor JSON display geometries."""
    detector = DesktopEnvironmentDetector()

    with patch("shutil.which", return_value="/usr/bin/kscreen-doctor"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["/usr/bin/kscreen-doctor", "-j"],
            returncode=0,
            stdout=SAMPLE_KSCREEN_JSON,
            stderr="",
        )

        displays = detector.detect_displays()
        assert len(displays) == 1

        edp = displays[0]
        assert edp.name == "eDP-1"
        assert edp.width == 1920
        assert edp.height == 1080
        assert edp.refresh_rate == 60.0
        assert edp.scale == 1.0
        assert edp.connected is True
        assert edp.enabled is True
        assert edp.is_primary is True


def test_environment_detector_kscreen_missing_or_invalid():
    """Verify graceful fallback when kscreen-doctor is missing or returns invalid JSON."""
    detector = DesktopEnvironmentDetector()

    with patch("shutil.which", return_value=None):
        displays = detector.detect_displays()
        assert len(displays) == 1
        assert "Primary" in displays[0].name
        assert displays[0].width == 1920
        assert displays[0].height == 1080

    with patch("shutil.which", return_value="/usr/bin/kscreen-doctor"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["/usr/bin/kscreen-doctor", "-j"],
            returncode=1,
            stdout="Invalid error",
            stderr="command failed",
        )
        displays = detector.detect_displays()
        assert len(displays) == 1
        assert "Primary" in displays[0].name


def test_environment_detector_tools_and_capabilities(tmp_path: Path):
    """Verify KDE utility discovery and capability mapping."""
    fake_config = tmp_path / "config"
    fake_config.mkdir()

    detector = DesktopEnvironmentDetector(config_dir=fake_config)
    env = detector.detect_environment()

    assert "plasma_version" in env
    assert "session_type" in env
    assert "distribution" in env
    assert "tools_available" in env
    assert "tools_paths" in env
    assert "capabilities" in env
    assert "unsupported_features" in env
    assert isinstance(env["displays"], list)

    caps = env["capabilities"]
    assert "config_file_inspection" in caps
    assert caps["arbitrary_widget_drag_drop"] is False
    assert caps["live_desktop_screenshot"] is False

    assert len(env["unsupported_features"]) >= 3


# ==============================================================================
# Layout Inspector Tests (Live D-Bus, Config, Correlate, Malformed)
# ==============================================================================

def test_dbus_dump_current_layout_success(tmp_path: Path):
    """Verify parsing live D-Bus layout data into typed models."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    appletsrc = config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
    appletsrc.write_text(SAMPLE_APPLETRC_CONTENT, encoding="utf-8")

    inspector = DesktopLayoutInspector(config_dir=config_dir)

    with patch("shutil.which", return_value="/usr/bin/qdbus6"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["/usr/bin/qdbus6", "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.dumpCurrentLayoutJS"],
            returncode=0,
            stdout=SAMPLE_DBUS_LAYOUT_JS,
            stderr="",
        )

        state = inspector.inspect_desktop()
        assert state.inspection_source == "live_system"
        assert len(state.panels) == 2

        # Top panel
        top_panel = next((p for p in state.panels if p.position == "top"), None)
        assert top_panel is not None
        assert top_panel.thickness == 40
        assert top_panel.visibility == "always_visible"
        assert top_panel.containment_id == "47"  # Correlated from on-disk config!
        assert len(top_panel.applets) == 2

        # Bottom dock
        bottom_dock = next((p for p in state.panels if p.position == "bottom"), None)
        assert bottom_dock is not None
        assert bottom_dock.is_dock is True
        assert bottom_dock.thickness == 56
        assert bottom_dock.visibility == "auto_hide"
        assert bottom_dock.containment_id == "61"  # Correlated from on-disk config!
        assert len(bottom_dock.applets) == 1

        # Desktop wallpaper & widgets
        assert state.wallpaper_image == "/home/user/Pictures/wallpaper.jpg"
        assert len(state.desktop_widgets) == 1
        assert state.desktop_widgets[0].title == "Modern Clock"


def test_dbus_timeout_fallback_to_config(tmp_path: Path):
    """Verify that a D-Bus timeout falls back to on-disk config inspection safely."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    appletsrc = config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
    appletsrc.write_text(SAMPLE_APPLETRC_CONTENT, encoding="utf-8")

    inspector = DesktopLayoutInspector(config_dir=config_dir)

    with patch("shutil.which", return_value="/usr/bin/qdbus6"), \
         patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="qdbus6", timeout=2.0)):

        state = inspector.inspect_desktop()
        # Should gracefully fall back to inferred_config
        assert state.inspection_source == "inferred_config"
        assert len(state.panels) == 2
        top_panel = next((p for p in state.panels if p.position == "top"), None)
        assert top_panel is not None
        assert top_panel.containment_id == "47"


def test_missing_qdbus_fallback_to_config(tmp_path: Path):
    """Verify fallback to config inspection when qdbus binary is not present."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    appletsrc = config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
    appletsrc.write_text(SAMPLE_APPLETRC_CONTENT, encoding="utf-8")

    inspector = DesktopLayoutInspector(config_dir=config_dir)

    with patch("shutil.which", return_value=None):
        state = inspector.inspect_desktop()
        assert state.inspection_source == "inferred_config"
        assert len(state.panels) == 2


def test_malformed_config_file_handling(tmp_path: Path):
    """Verify that a corrupted desktop-appletsrc file returns an 'unavailable' state without crashing."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    appletsrc = config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
    appletsrc.write_text("THIS IS COMPLETELY CORRUPTED GARBAGE \x00\x01\x02 [Containments", encoding="utf-8")

    inspector = DesktopLayoutInspector(config_dir=config_dir)

    with patch("shutil.which", return_value=None):
        state = inspector.inspect_desktop()
        # Returns unavailable or empty panels rather than throwing unhandled exception
        assert state.inspection_source in ("unavailable", "inferred_config")
        assert len(state.panels) == 0


def test_missing_config_file_handling(tmp_path: Path):
    """Verify that a non-existent config path returns an honest empty state."""
    config_dir = tmp_path / "non_existent_dir"
    inspector = DesktopLayoutInspector(config_dir=config_dir)

    with patch("shutil.which", return_value=None):
        state = inspector.inspect_desktop()
        assert state.inspection_source == "unavailable"
        assert len(state.panels) == 0
        assert "does not exist" in state.status_message


def test_read_only_guarantee(tmp_path: Path):
    """Verify that inspecting the desktop strictly avoids writing to or altering configuration files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    appletsrc = config_dir / "plasma-org.kde.plasma.desktop-appletsrc"
    appletsrc.write_text(SAMPLE_APPLETRC_CONTENT, encoding="utf-8")

    sha_before = hashlib.sha256(appletsrc.read_bytes()).hexdigest()

    detector = DesktopEnvironmentDetector(config_dir=config_dir)
    inspector = DesktopLayoutInspector(detector=detector, config_dir=config_dir)

    # Run multiple inspection passes
    state1 = inspector.inspect_desktop()
    state2 = inspector.inspect_desktop()

    sha_after = hashlib.sha256(appletsrc.read_bytes()).hexdigest()
    assert sha_before == sha_after, "Inspection must never alter or rewrite config files on disk!"


# ==============================================================================
# Change Analyzer Tests
# ==============================================================================

def test_change_analyzer_detected_vs_draft():
    """Verify DesktopChangeAnalyzer detects exact property differences."""
    base_layout = DesktopLayout(
        id="base",
        name="Base",
        description="",
        top_panel=PanelConfig(position="top", thickness=36, visibility="always_visible"),
        dock=PanelConfig(position="bottom", thickness=48, visibility="always_visible", is_dock=True),
        show_widgets=False,
    )

    draft_layout = DesktopLayout(
        id="draft",
        name="Draft",
        description="",
        top_panel=PanelConfig(position="bottom", thickness=48, visibility="auto_hide"),
        dock=PanelConfig(position="top", thickness=64, visibility="dodge_windows", is_dock=True),
        show_widgets=True,
    )

    changes = DesktopChangeAnalyzer.compare_states(base_layout, draft_layout)
    assert len(changes) == 7

    components = {c.component: c for c in changes}
    assert "Top Panel Edge Position" in components
    assert components["Top Panel Edge Position"].current_value == "top"
    assert components["Top Panel Edge Position"].proposed_value == "bottom"
    assert components["Top Panel Edge Position"].is_supported_live is True

    assert "Top Panel Thickness" in components
    assert components["Top Panel Thickness"].current_value == "36px"
    assert components["Top Panel Thickness"].proposed_value == "48px"

    assert "Top Panel Visibility Mode" in components
    assert "Dock Edge Position" in components
    assert "Dock Thickness" in components
    assert "Dock Visibility Mode" in components

    assert "Desktop Widgets Layer" in components
    assert components["Desktop Widgets Layer"].is_supported_live is False


def test_change_analyzer_no_changes_when_matching():
    """Verify DesktopChangeAnalyzer returns 0 proposed changes when draft matches current state."""
    base_layout = DesktopLayout(
        id="base",
        name="Base",
        description="",
        top_panel=PanelConfig(position="top", thickness=36, visibility="always_visible"),
        dock=PanelConfig(position="bottom", thickness=48, visibility="always_visible", is_dock=True),
        show_widgets=False,
    )

    changes = DesktopChangeAnalyzer.compare_states(base_layout, base_layout)
    assert len(changes) == 0


# ==============================================================================
# Controller Integration Tests
# ==============================================================================

def test_controller_inspection_integration(qapp):
    """Verify DesktopController exposes live inspection properties and reacts to workbench changes."""
    ctrl = DesktopController()

    # Properties exposed
    assert isinstance(ctrl.isInspecting, bool)
    assert isinstance(ctrl.lastInspectionTime, str)
    assert ctrl.inspectionSource in ("live_system", "inferred_config", "unavailable")
    assert isinstance(ctrl.inspectionStatusText, str)
    assert isinstance(ctrl.environmentInfo, dict)
    assert isinstance(ctrl.livePanels, list)
    assert isinstance(ctrl.liveDesktopWidgets, list)
    assert isinstance(ctrl.liveWallpaper, str)
    assert isinstance(ctrl.inspectionCapabilities, dict)
    assert isinstance(ctrl.unsupportedFeatures, list)
    assert isinstance(ctrl.proposedChanges, list)
    assert ctrl.hasProposedChanges is False

    # Tweaking draft creates proposed changes
    ctrl.setPanelPosition("bottom")
    assert ctrl.isDraftModified is True
    assert ctrl.hasProposedChanges is True
    assert len(ctrl.proposedChanges) >= 1

    # Resetting draft clears proposed changes
    ctrl.resetDraft()
    assert ctrl.isDraftModified is False
    assert ctrl.hasProposedChanges is False
    assert len(ctrl.proposedChanges) == 0
