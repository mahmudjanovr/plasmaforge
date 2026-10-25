"""Unit tests for Phase 5 Setup Gallery: profile models, schema validation, import/export, and controller workflows."""

import json
from pathlib import Path
from typing import Any, Dict

import pytest
from PySide6.QtGui import QGuiApplication

from plasmaforge.controllers.desktop_controller import DesktopController
from plasmaforge.controllers.preset_controller import PresetController
from plasmaforge.controllers.theme_controller import ThemeController
from plasmaforge.core.desktop_layout import DesktopLayout, PanelConfig
from plasmaforge.core.profiles import (
    ColorSchemeSpec,
    ProfileManager,
    ProfileValidationError,
    SetupProfile,
    get_curated_profiles,
)


def test_curated_profiles_validity() -> None:
    """Verify built-in curated setup profiles are fully valid under schema v1."""
    profiles = get_curated_profiles()
    assert len(profiles) >= 4

    categories = {p.category for p in profiles}
    assert "Productivity" in categories
    assert "Minimal" in categories
    assert "Nothing-Inspired" in categories

    for p in profiles:
        assert p.schema_version == 1
        assert p.id
        assert p.name
        assert p.tagline
        assert p.description
        assert p.color_scheme.scheme_id
        assert p.desktop_layout.top_panel.position in ["top", "bottom", "left", "right", "none"]
        assert p.desktop_layout.dock.position in ["top", "bottom", "left", "right", "none"]
        assert p.color_scheme.preview_colors.get("bg", "").startswith("#")
        assert p.color_scheme.preview_colors.get("surface", "").startswith("#")
        assert p.color_scheme.preview_colors.get("accent", "").startswith("#")
        assert p.color_scheme.preview_colors.get("text", "").startswith("#")
        errors = p.validate()
        assert not errors, f"Curated profile {p.id} has validation errors: {errors}"


def test_profile_schema_validation_rejections() -> None:
    """Ensure invalid profile structures and schemas are strictly rejected."""
    valid_base = get_curated_profiles()[0].to_dict()

    # Reject unsupported schema version
    bad_ver = dict(valid_base)
    bad_ver["schema_version"] = 2
    with pytest.raises(ProfileValidationError, match="Unsupported profile schema version"):
        SetupProfile.from_dict(bad_ver)

    # Reject missing id
    no_id = dict(valid_base)
    no_id["id"] = ""
    with pytest.raises(ProfileValidationError, match="Invalid profile ID"):
        SetupProfile.from_dict(no_id)

    # Reject missing name
    no_name = dict(valid_base)
    no_name["name"] = ""
    with pytest.raises(ProfileValidationError, match="Profile name must be non-empty"):
        SetupProfile.from_dict(no_name)

    # Reject missing color scheme
    no_cs = dict(valid_base)
    no_cs.pop("color_scheme")
    with pytest.raises(ProfileValidationError, match="color_scheme"):
        SetupProfile.from_dict(no_cs)

    # Reject out-of-bounds panel thickness
    bad_panel = dict(valid_base)
    bad_panel_layout = dict(valid_base["desktop_layout"])
    bad_panel_layout["top_panel"] = dict(bad_panel_layout["top_panel"])
    bad_panel_layout["top_panel"]["thickness"] = 200
    bad_panel["desktop_layout"] = bad_panel_layout
    with pytest.raises(ProfileValidationError, match="out of bounds"):
        SetupProfile.from_dict(bad_panel)

    # Reject invalid hex color
    bad_color = dict(valid_base)
    bad_color["color_scheme"] = dict(valid_base["color_scheme"])
    bad_color["color_scheme"]["preview_colors"] = dict(bad_color["color_scheme"]["preview_colors"])
    bad_color["color_scheme"]["preview_colors"]["accent"] = "not_a_hex"
    with pytest.raises(ProfileValidationError, match="Invalid preview color"):
        SetupProfile.from_dict(bad_color)


def test_rejection_of_forbidden_keys() -> None:
    """Security check: Reject profiles containing executable/shell command keys."""
    valid_base = get_curated_profiles()[0].to_dict()

    forbidden_names = ["exec", "command", "script", "shell", "run", "eval", "system", "subprocess"]
    for key in forbidden_names:
        # In root
        payload = dict(valid_base)
        payload[key] = "echo pwned"
        with pytest.raises(ProfileValidationError, match="Forbidden executable key"):
            SetupProfile.from_dict(payload)

        # In simulated_features
        payload_sim = dict(valid_base)
        payload_sim["simulated_features"] = dict(payload_sim.get("simulated_features", {}))
        payload_sim["simulated_features"][key] = "rm -rf /"
        with pytest.raises(ProfileValidationError, match="Forbidden key .* detected in simulated features"):
            SetupProfile.from_dict(payload_sim)


def test_rejection_of_oversized_and_malformed_profiles(tmp_path: Path) -> None:
    """Ensure oversized profile files and malformed JSON are safely rejected by manager."""
    mgr = ProfileManager(storage_dir=tmp_path / "profiles")

    # Oversized file (> 512 KB)
    big_file = tmp_path / "oversized.json"
    big_file.write_text(" " * (512 * 1024 + 10))
    ok, msg, prof = mgr.import_profile_file(big_file)
    assert not ok
    assert "exceeds maximum limit" in msg
    assert prof is None

    # Malformed JSON syntax
    bad_syntax = tmp_path / "broken.json"
    bad_syntax.write_text("{\"schema_version\": 1, unquoted_key: 123")
    ok, msg, prof = mgr.import_profile_file(bad_syntax)
    assert not ok
    assert "Malformed JSON" in msg
    assert prof is None


    # Valid JSON but not a dictionary (e.g. array)
    array_json = tmp_path / "array.json"
    array_json.write_text("[1, 2, 3]")
    ok, msg, prof = mgr.import_profile_file(array_json)
    assert not ok
    assert "Profile root must be a JSON object" in msg
    assert prof is None


def test_profile_import_export_roundtrip(tmp_path: Path) -> None:
    """Test exporting a profile to JSON and importing it back into ProfileManager."""
    storage_dir = tmp_path / "custom_profiles"
    export_dest = tmp_path / "exports" / "exported_nothing.json"

    mgr = ProfileManager(storage_dir=storage_dir)

    # Export 'nothing_inspired' profile
    ok, msg = mgr.export_profile("nothing_inspired", export_dest)
    assert ok, f"Export failed: {msg}"
    assert export_dest.exists()

    content = json.loads(export_dest.read_text(encoding="utf-8"))
    assert content["schema_version"] == 1
    assert content["id"] == "nothing_inspired"
    assert content["category"] == "Nothing-Inspired"

    # Now import exported file into a secondary clean manager
    secondary_storage = tmp_path / "secondary_profiles"
    mgr2 = ProfileManager(storage_dir=secondary_storage)

    # Initial state has curated profiles only
    initial_count = len(mgr2.list_profiles())

    ok, msg, imported = mgr2.import_profile_file(export_dest)
    assert ok, f"Import failed: {msg}"
    assert imported is not None
    assert imported.is_user_imported is True
    # Duplicate ID got suffixed so it didn't clash with built-in
    assert imported.id == "nothing_inspired_1"
    assert (secondary_storage / "nothing_inspired_1.json").exists()

    # Total profiles in secondary manager increased by 1
    assert len(mgr2.list_profiles()) == initial_count + 1


def test_duplicate_profile_id_resolution(tmp_path: Path) -> None:
    """Ensure duplicate profile imports get distinct sequential IDs."""
    mgr = ProfileManager(storage_dir=tmp_path / "profiles")
    base_prof = get_curated_profiles()[0].to_dict()
    base_prof["id"] = "unique_theme"
    base_prof["name"] = "Unique Custom Theme"

    # Import #1
    ok1, _, p1 = mgr.import_profile_json(json.dumps(base_prof))
    assert ok1
    assert p1.id == "unique_theme"

    # Import #2 with same ID -> resolves to unique_theme_1
    ok2, _, p2 = mgr.import_profile_json(json.dumps(base_prof))
    assert ok2
    assert p2.id == "unique_theme_1"

    # Import #3 with same ID -> resolves to unique_theme_2
    ok3, _, p3 = mgr.import_profile_json(json.dumps(base_prof))
    assert ok3
    assert p3.id == "unique_theme_2"


def test_isolation_guarantee(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify profile operations NEVER touch live ~/.config files directly."""
    fake_kde_home = tmp_path / "fake_kde"
    config_dir = fake_kde_home / ".config"
    config_dir.mkdir(parents=True)
    kdeglobals = config_dir / "kdeglobals"
    plasma_applets = config_dir / "plasma-org.kde.plasma.desktop-appletsrc"

    kdeglobals.write_text("[General]\nColorScheme=Original\n")
    plasma_applets.write_text("[Containments][1]\nlocation=top\n")

    monkeypatch.setenv("HOME", str(fake_kde_home))

    mgr = ProfileManager(storage_dir=tmp_path / "test_profiles")
    # Export and import actions
    mgr.export_profile("obsidian_teal", tmp_path / "obsidian.json")
    mgr.import_profile_file(tmp_path / "obsidian.json")

    # Verify live files remain completely untouched
    assert kdeglobals.read_text() == "[General]\nColorScheme=Original\n"
    assert plasma_applets.read_text() == "[Containments][1]\nlocation=top\n"


def test_preset_controller_filtering_and_search(qapp: QGuiApplication) -> None:
    """Verify PresetController category filtering and search queries."""
    ctrl = PresetController()
    initial_count = ctrl.profileCount
    assert initial_count >= 4

    # Filter by Nothing-Inspired category
    ctrl.setCategory("Nothing-Inspired")
    assert ctrl.selectedCategory == "Nothing-Inspired"
    assert ctrl.profileCount >= 1
    for p in ctrl.profiles:
        assert p["category"] == "Nothing-Inspired"

    # Filter by Minimal
    ctrl.setCategory("Minimal")
    assert ctrl.selectedCategory == "Minimal"
    for p in ctrl.profiles:
        assert p["category"] == "Minimal"

    # Reset to All
    ctrl.setCategory("All")
    assert ctrl.profileCount == initial_count

    # Search query
    ctrl.setSearchQuery("nothing")
    assert ctrl.searchQuery == "nothing"
    assert ctrl.profileCount >= 1
    assert any("nothing" in p["name"].lower() for p in ctrl.profiles)

    # Empty search query match
    ctrl.setSearchQuery("non_existent_search_query_12345")
    assert ctrl.profileCount == 0

    # Clear query
    ctrl.setSearchQuery("")
    assert ctrl.profileCount == initial_count


def test_preset_controller_workbench_transfers(qapp: QGuiApplication) -> None:
    """Verify PresetController workbench transfer signal emissions."""
    ctrl = PresetController()
    ctrl.setCategory("Nothing-Inspired")
    ctrl.selectProfile(0)

    # Track emitted signals
    layout_transferred = []
    theme_transferred = []
    ops_completed = []

    ctrl.layoutTransferRequested.connect(layout_transferred.append)
    ctrl.themeTransferRequested.connect(theme_transferred.append)
    ctrl.profileOperationCompleted.connect(lambda msg, ok: ops_completed.append((msg, ok)))

    # Transfer layout to Desktop Builder draft
    ctrl.loadLayoutIntoDesktopBuilder()
    assert len(layout_transferred) == 1
    assert "top_panel" in layout_transferred[0]
    assert "dock" in layout_transferred[0]
    assert any(ok for msg, ok in ops_completed)

    # Transfer color scheme to Theme Studio
    ctrl.applyColorSchemeViaThemeStudio()
    assert len(theme_transferred) == 1
    assert theme_transferred[0] == "Nothing"


def test_desktop_controller_load_draft_from_dict(qapp: QGuiApplication) -> None:
    """Verify DesktopController correctly loads layout dictionary into draft workbench."""
    desktop_ctrl = DesktopController()
    curated = get_curated_profiles()[1].desktop_layout.to_dict()

    desktop_ctrl.loadDraftFromDict(curated)
    assert desktop_ctrl.draftLayout["id"] == curated["id"]
    assert desktop_ctrl.draftLayout["top_panel"]["position"] == curated["top_panel"]["position"]
    assert desktop_ctrl.draftLayout["dock"]["thickness"] == curated["dock"]["thickness"]
    assert desktop_ctrl.isDraftModified is True
