"""Comprehensive tests for Installed Widget Catalog, Layout Presets, KdeWidgetPlacer, and DesktopBuilder integrations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest
from PySide6.QtGui import QGuiApplication

from plasmaforge.controllers.desktop_controller import DesktopController
from plasmaforge.core.desktop_inspector import DesktopChangeAnalyzer
from plasmaforge.core.desktop_layout import DesktopLayout, PanelConfig
from plasmaforge.core.kde_widget_placer import KdeWidgetPlacer
from plasmaforge.core.layout_presets import (
    LayoutPreset,
    LayoutPresetManager,
    get_curated_layout_presets,
)
from plasmaforge.core.widget_catalog import (
    InstalledWidgetInfo,
    WidgetCatalogService,
)


# ==============================================================================
# 1. Widget Catalog Discovery Tests
# ==============================================================================

def test_widget_catalog_real_discovery(tmp_path: Path) -> None:
    """Verify WidgetCatalogService discovers widgets or handles empty environment gracefully."""
    service = WidgetCatalogService()
    widgets = service.get_installed_widgets(force_refresh=True)

    assert isinstance(widgets, list)
    # On an Arch Linux KDE Plasma 6 workstation, there should be installed widgets
    for w in widgets:
        assert isinstance(w, InstalledWidgetInfo)
        assert w.plugin_id
        assert w.name
        assert w.source in ("user_installed", "system_package")
        assert w.is_installed is True
        assert isinstance(w.suitable_for, list)


def test_widget_catalog_mock_discovery(tmp_path: Path) -> None:
    """Verify parsing of metadata.json and metadata.desktop in isolated test directory."""
    user_dir = tmp_path / "user_plasmoids"
    sys_dir = tmp_path / "sys_plasmoids"
    qt_dir = tmp_path / "qt_plugins"

    user_dir.mkdir()
    sys_dir.mkdir()
    qt_dir.mkdir()

    # 1. User plasmoid with metadata.json
    plasmoid_1 = user_dir / "com.example.testwidget"
    plasmoid_1.mkdir()
    meta_json_1 = plasmoid_1 / "metadata.json"
    meta_json_1.write_text(
        json.dumps({
            "KPlugin": {
                "Id": "com.example.testwidget",
                "Name": "Test Widget",
                "Description": "A test user widget.",
                "Category": "Date and Time",
                "Icon": "preferences-system-time",
                "Version": "1.2.0",
                "Authors": [{"Name": "Tester"}],
            }
        }),
        encoding="utf-8",
    )

    # 2. System plasmoid with metadata.desktop fallback
    plasmoid_2 = sys_dir / "org.kde.example.legacy"
    plasmoid_2.mkdir()
    meta_desk_2 = plasmoid_2 / "metadata.desktop"
    meta_desk_2.write_text(
        "[Desktop Entry]\n"
        "Name=Legacy Widget\n"
        "Comment=A legacy system widget.\n"
        "X-KDE-PluginInfo-Category=Utilities\n"
        "Icon=utilities-terminal\n"
        "X-KDE-PluginInfo-Author=KDE Team\n"
        "X-KDE-PluginInfo-Version=2.0\n",
        encoding="utf-8",
    )

    # 3. Qt binary applet
    so_file = qt_dir / "plasma_applet_customclock.so"
    so_file.write_bytes(b"\x7fELFfakebinary")

    service = WidgetCatalogService(
        user_plasmoids_dir=user_dir,
        system_plasmoids_dir=sys_dir,
        system_applets_dir=qt_dir,
    )

    widgets = service.get_installed_widgets(force_refresh=True)
    plugin_ids = {w.plugin_id: w for w in widgets}

    assert "com.example.testwidget" in plugin_ids
    assert plugin_ids["com.example.testwidget"].name == "Test Widget"
    assert plugin_ids["com.example.testwidget"].description == "A test user widget."
    assert plugin_ids["com.example.testwidget"].source == "user_installed"
    assert plugin_ids["com.example.testwidget"].category == "Date and Time"

    assert "org.kde.example.legacy" in plugin_ids
    assert plugin_ids["org.kde.example.legacy"].name == "Legacy Widget"
    assert plugin_ids["org.kde.example.legacy"].source == "system_package"
    assert plugin_ids["org.kde.example.legacy"].category == "Utilities"

    assert "plasma_applet_customclock" in plugin_ids
    assert plugin_ids["plasma_applet_customclock"].source == "system_package"


def test_widget_catalog_search_and_categories(tmp_path: Path) -> None:
    """Verify categories extraction and search filtering."""
    user_dir = tmp_path / "user_plasmoids"
    user_dir.mkdir()

    p1 = user_dir / "org.test.clock"
    p1.mkdir()
    (p1 / "metadata.json").write_text(
        json.dumps({"KPlugin": {"Id": "org.test.clock", "Name": "Fancy Clock", "Category": "Date and Time"}}),
        encoding="utf-8",
    )

    p2 = user_dir / "org.test.launcher"
    p2.mkdir()
    (p2 / "metadata.json").write_text(
        json.dumps({"KPlugin": {"Id": "org.test.launcher", "Name": "App Launcher", "Category": "Application Launchers"}}),
        encoding="utf-8",
    )

    service = WidgetCatalogService(
        user_plasmoids_dir=user_dir,
        system_plasmoids_dir=tmp_path / "empty1",
        system_applets_dir=tmp_path / "empty2",
    )

    cats = service.get_categories()
    assert "Date and Time" in cats
    assert "Application Launchers" in cats

    # Search by text
    results = service.search_widgets(query="clock")
    assert len(results) == 1
    assert results[0].plugin_id == "org.test.clock"

    # Search by category
    results = service.search_widgets(category="Application Launchers")
    assert len(results) == 1
    assert results[0].plugin_id == "org.test.launcher"

    # Find widget & is_widget_installed
    assert service.is_widget_installed("org.test.clock") is True
    assert service.is_widget_installed("org.nonexistent") is False
    found = service.find_widget("org.test.clock")
    assert found is not None
    assert found.name == "Fancy Clock"


def test_widget_catalog_corrupted_metadata_resilience(tmp_path: Path) -> None:
    """Verify corrupted JSON or malformed files do not crash discovery."""
    user_dir = tmp_path / "user_plasmoids"
    user_dir.mkdir()

    p_broken = user_dir / "org.test.broken"
    p_broken.mkdir()
    (p_broken / "metadata.json").write_text("{this is not valid json!}", encoding="utf-8")

    service = WidgetCatalogService(
        user_plasmoids_dir=user_dir,
        system_plasmoids_dir=tmp_path / "empty1",
        system_applets_dir=tmp_path / "empty2",
    )

    widgets = service.get_installed_widgets()
    assert len(widgets) == 1
    assert widgets[0].plugin_id == "org.test.broken"
    assert widgets[0].name != ""


# ==============================================================================
# 2. Layout Presets and Preset Manager Tests
# ==============================================================================

def test_curated_layout_presets_validation() -> None:
    """Verify built-in curated presets satisfy schema requirements."""
    presets = get_curated_layout_presets()
    assert len(presets) >= 4
    preset_ids = {p.id for p in presets}
    assert "classic_kde" in preset_ids
    assert "nothing_inspired" in preset_ids
    assert "clean_minimal" in preset_ids
    assert "dual_status_dock" in preset_ids

    for p in presets:
        errors = p.validate()
        assert not errors, f"Preset '{p.id}' failed validation: {errors}"
        assert p.is_builtin is True
        layout = p.to_desktop_layout()
        assert isinstance(layout, DesktopLayout)
        assert layout.id == p.id
        assert layout.top_panel is not None
        assert layout.dock is not None


def test_layout_preset_manager_save_and_delete(tmp_path: Path) -> None:
    """Verify atomic saving, loading, and deletion of custom layout presets."""
    mgr = LayoutPresetManager(storage_dir=tmp_path)

    custom_preset = LayoutPreset(
        id="my_custom_preset",
        name="My Custom Preset",
        description="A test user preset.",
        author="Tester",
        top_panel=PanelConfig(position="top", thickness=38, visibility="always_visible", applets=["org.kde.plasma.kickoff"]),
        dock=PanelConfig(position="bottom", thickness=50, visibility="dodge_windows", is_dock=True, applets=["org.kde.plasma.icontasks"]),
        desktop_widgets=["com.example.widget"],
        required_widgets=["org.kde.plasma.kickoff", "org.kde.plasma.icontasks"],
        is_builtin=False,
    )

    # Save
    ok, msg = mgr.save_preset(custom_preset)
    assert ok is True
    assert (tmp_path / "my_custom_preset.json").is_file()

    # Load back
    loaded = mgr.get_preset("my_custom_preset")
    assert loaded is not None
    assert loaded.name == "My Custom Preset"
    assert loaded.top_panel.thickness == 38
    assert loaded.dock.applets == ["org.kde.plasma.icontasks"]
    assert loaded.desktop_widgets == ["com.example.widget"]
    assert loaded.is_builtin is False

    # Refuse overwrite if not requested
    ok2, _ = mgr.save_preset(custom_preset, overwrite=False)
    assert ok2 is False

    # Overwrite if requested
    custom_preset.name = "Updated Name"
    ok3, _ = mgr.save_preset(custom_preset, overwrite=True)
    assert ok3 is True
    assert mgr.get_preset("my_custom_preset").name == "Updated Name"

    # Cannot overwrite builtin presets
    builtin = get_curated_layout_presets()[0]
    ok_builtin, _ = mgr.save_preset(builtin)
    assert ok_builtin is False

    # Delete
    del_ok, _ = mgr.delete_preset("my_custom_preset")
    assert del_ok is True
    assert not (tmp_path / "my_custom_preset.json").exists()
    assert mgr.get_preset("my_custom_preset") is None

    # Cannot delete builtin
    del_builtin_ok, _ = mgr.delete_preset("classic_kde")
    assert del_builtin_ok is False


def test_preset_check_missing_widgets(tmp_path: Path) -> None:
    """Verify missing required widgets detection."""
    user_dir = tmp_path / "user_plasmoids"
    user_dir.mkdir()
    # Install only kickoff
    p1 = user_dir / "org.kde.plasma.kickoff"
    p1.mkdir()
    (p1 / "metadata.json").write_text(json.dumps({"KPlugin": {"Id": "org.kde.plasma.kickoff"}}), encoding="utf-8")

    catalog = WidgetCatalogService(
        user_plasmoids_dir=user_dir,
        system_plasmoids_dir=tmp_path / "empty1",
        system_applets_dir=tmp_path / "empty2",
    )

    mgr = LayoutPresetManager(storage_dir=tmp_path / "presets")
    preset = LayoutPreset(
        id="check_missing",
        name="Missing Test",
        description="Test missing",
        author="Tester",
        top_panel=PanelConfig(position="top", thickness=32),
        dock=PanelConfig(position="bottom", thickness=48),
        required_widgets=["org.kde.plasma.kickoff", "org.kde.plasma.missing1", "org.kde.plasma.missing2"],
        is_builtin=False,
    )
    mgr.save_preset(preset)

    missing = mgr.check_missing_widgets("check_missing", catalog)
    assert "org.kde.plasma.missing1" in missing
    assert "org.kde.plasma.missing2" in missing
    assert "org.kde.plasma.kickoff" not in missing


# ==============================================================================
# 3. KdeWidgetPlacer Security and Script Tests
# ==============================================================================

def test_kde_widget_placer_input_validation() -> None:
    """Verify KdeWidgetPlacer strictly rejects script injection attempts."""
    placer = KdeWidgetPlacer()

    # Rejection of invalid characters
    assert placer.add_widget_to_containment("46", "org.kde.plasma.kickoff; rm -rf /").success is False
    assert placer.add_widget_to_containment("46", "org.kde.plasma.kickoff'").success is False
    assert placer.add_widget_to_containment("46", 'org.kde.plasma.kickoff"').success is False
    assert placer.add_widget_to_containment("invalid_cid_!!", "org.kde.plasma.kickoff").success is False
    assert placer.add_widget_to_containment("46", "").success is False

    # Valid format check
    assert placer.is_valid_plugin_id("org.kde.plasma.kickoff") is True
    assert placer.is_valid_plugin_id("com.github.prayag2.modernclock") is True
    assert placer.is_valid_plugin_id("invalid id with spaces") is False


def test_kde_widget_placer_script_generation() -> None:
    """Verify D-Bus script generation syntax."""
    placer = KdeWidgetPlacer()

    script = placer._build_add_widget_script("46", "org.kde.plasma.digitalclock")
    assert "panelById(46)" in script or "panelById('46')" in script or "desktops()" in script
    assert "addWidget('org.kde.plasma.digitalclock')" in script

    remove_script = placer._build_remove_widget_script("46", 123)
    assert "123" in remove_script
    assert "widgetById(123).remove()" in remove_script or "remove()" in remove_script


# ==============================================================================
# 4. DesktopController Widget Catalog & Presets Integration Tests
# ==============================================================================

def test_desktop_controller_widget_catalog_and_presets(qapp: QGuiApplication, tmp_path: Path) -> None:
    """Verify DesktopController exposes catalog, search, applet staging, and preset saving."""
    user_plasmoids = tmp_path / "user_plasmoids"
    user_plasmoids.mkdir()
    p1 = user_plasmoids / "org.kde.plasma.testapplet"
    p1.mkdir()
    (p1 / "metadata.json").write_text(
        json.dumps({
            "KPlugin": {
                "Id": "org.kde.plasma.testapplet",
                "Name": "Test Applet",
                "Description": "An applet for testing.",
                "Category": "Utilities",
            }
        }),
        encoding="utf-8",
    )

    catalog = WidgetCatalogService(
        user_plasmoids_dir=user_plasmoids,
        system_plasmoids_dir=tmp_path / "empty1",
        system_applets_dir=tmp_path / "empty2",
    )
    presets_dir = tmp_path / "user_presets"
    preset_mgr = LayoutPresetManager(storage_dir=presets_dir)

    ctrl = DesktopController(
        catalog_service=catalog,
        preset_manager=preset_mgr,
    )

    # Initial state
    assert ctrl.widgetCategories is not None
    assert len(ctrl.presets) >= 4

    # Search widgets slot
    search_res = ctrl.searchWidgets("Test Applet", "", "")
    assert len(search_res) == 1
    assert search_res[0]["plugin_id"] == "org.kde.plasma.testapplet"

    # Stage applet to panel
    initial_applets_count = len(ctrl.selectedPanelApplets)
    ok_add = ctrl.addAppletToDraft(ctrl.selectedPanelId, "org.kde.plasma.testapplet")
    assert ok_add is True
    assert len(ctrl.selectedPanelApplets) == initial_applets_count + 1
    assert "org.kde.plasma.testapplet" in ctrl.selectedPanelApplets
    assert ctrl.isDraftModified is True

    # Reorder applets
    ctrl.addAppletToDraft(ctrl.selectedPanelId, "org.kde.plasma.secondapplet")
    applets = ctrl.selectedPanelApplets
    idx_second = applets.index("org.kde.plasma.secondapplet")
    ctrl.moveAppletInDraft(ctrl.selectedPanelId, idx_second, 0)
    assert ctrl.selectedPanelApplets[0] == "org.kde.plasma.secondapplet"

    # Remove applet from panel
    ok_rem = ctrl.removeAppletFromDraft(ctrl.selectedPanelId, 0)
    assert ok_rem is True
    assert "org.kde.plasma.secondapplet" not in ctrl.selectedPanelApplets

    # Stage desktop widget
    ok_dw = ctrl.addDesktopWidgetToDraft("com.example.desktopclock")
    assert ok_dw is True
    assert "com.example.desktopclock" in ctrl.desktopWidgets
    assert ctrl.showWidgets is True

    ok_dw_rem = ctrl.removeDesktopWidgetFromDraft(0)
    assert ok_dw_rem is True
    assert "com.example.desktopclock" not in ctrl.desktopWidgets

    # Save draft as custom preset
    ok_save = ctrl.saveDraftAsPreset("my_test_preset", "My Test Preset", "A test description")
    assert ok_save is True
    assert (presets_dir / "my_test_preset.json").is_file()
    custom_ids = [p["id"] for p in ctrl.customPresets]
    assert "my_test_preset" in custom_ids

    # Delete custom preset
    ok_del = ctrl.deleteCustomPreset("my_test_preset")
    assert ok_del is True
    assert not (presets_dir / "my_test_preset.json").exists()


def test_desktop_change_analyzer_includes_applets() -> None:
    """Verify DesktopChangeAnalyzer highlights applet additions and removals."""
    cur = DesktopLayout(
        id="cur",
        name="Current",
        top_panel=PanelConfig(position="top", thickness=32, visibility="always_visible", applets=["org.kde.plasma.kickoff"]),
        dock=PanelConfig(position="bottom", thickness=48, visibility="always_visible", applets=["org.kde.plasma.icontasks"]),
    )

    draft = DesktopLayout(
        id="draft",
        name="Draft",
        top_panel=PanelConfig(position="top", thickness=32, visibility="always_visible", applets=["org.kde.plasma.kickoff", "org.kde.plasma.digitalclock"]),
        dock=PanelConfig(position="bottom", thickness=48, visibility="always_visible", applets=[]),
    )

    changes = DesktopChangeAnalyzer.compare_states(cur, draft)
    change_components = {c.component: c for c in changes}

    assert "Top Panel Applets" in change_components
    top_change = change_components["Top Panel Applets"]
    assert "Add org.kde.plasma.digitalclock" in top_change.description

    assert "Dock Applets" in change_components
    dock_change = change_components["Dock Applets"]
    assert "Remove org.kde.plasma.icontasks" in dock_change.description
