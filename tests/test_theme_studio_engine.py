"""Tests for Theme Studio reactive theme engine, live state editing, and persistent JSON presets."""

from pathlib import Path
import pytest
from PySide6.QtGui import QGuiApplication

from plasmaforge.core.theme_presets import (
    ThemeColors,
    ThemePreset,
    ThemePresetManager,
    ThemeTypography,
    ThemeValidationError,
    get_builtin_theme_presets,
    slugify_name,
)
from plasmaforge.controllers.theme_controller import ThemeController


@pytest.fixture(scope="session")
def qapp() -> QGuiApplication:
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(["test", "-platform", "offscreen"])
    return app


def test_builtin_theme_presets() -> None:
    presets = get_builtin_theme_presets()
    assert len(presets) >= 4
    preset_ids = [p.id for p in presets]
    assert "plasmaforge_teal" in preset_ids
    assert "nordic_horizon" in preset_ids
    assert "arch_minimalist" in preset_ids
    assert "paper_umber" in preset_ids

    for p in presets:
        assert p.is_builtin is True
        errors = p.validate()
        assert len(errors) == 0, f"Built-in preset '{p.id}' had validation errors: {errors}"
        assert p.colors.primary.startswith("#")
        assert p.colors.background.startswith("#")
        assert p.colors.surface.startswith("#")
        assert p.colors.text.startswith("#")
        assert p.colors.secondary_text.startswith("#")
        assert p.typography.font_family != ""
        assert 9 <= p.typography.font_size <= 24
        assert 0 <= p.border_radius <= 32
        assert 0.5 <= p.spacing_scale <= 2.5


def test_theme_preset_validation() -> None:
    # Valid preset
    valid_preset = ThemePreset(
        id="custom_teal",
        name="Custom Teal",
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
    )
    assert valid_preset.validate() == []

    # Invalid hex colors
    invalid_color_preset = ThemePreset(
        id="bad_color",
        name="Bad Color",
        colors=ThemeColors(primary="red", background="not-a-color"),
    )
    errors = invalid_color_preset.validate()
    assert any("Invalid hex color" in e for e in errors)

    # Invalid geometry bounds
    invalid_geo_preset = ThemePreset(
        id="bad_geo",
        name="Bad Geometry",
        border_radius=99,
        spacing_scale=5.0,
    )
    errors = invalid_geo_preset.validate()
    assert any("Border radius" in e for e in errors)
    assert any("Spacing scale" in e for e in errors)

    # Forbidden security keys in dictionary parsing
    with pytest.raises(ThemeValidationError, match="Forbidden key"):
        ThemePreset.from_dict({
            "id": "exploit",
            "name": "Exploit",
            "exec": "rm -rf /",
            "colors": {},
        })


def test_preset_manager_save_and_persistence(tmp_path: Path) -> None:
    manager = ThemePresetManager(storage_dir=tmp_path)
    initial_count = len(manager.list_presets())

    custom = ThemePreset(
        id="cyber_sunset",
        name="Cyber Sunset",
        description="Vibrant neon orange and magenta studio theme",
        colors=ThemeColors(
            primary="#ff5500",
            background="#0d0e12",
            surface="#15171e",
            text="#ffffff",
            secondary_text="#a0a4b0",
        ),
        typography=ThemeTypography(font_family="JetBrains Mono", font_size=14),
        border_radius=8,
        spacing_scale=1.1,
    )

    ok, msg = manager.save_preset(custom)
    assert ok is True
    assert "saved successfully" in msg
    assert (tmp_path / "cyber_sunset.json").is_file()

    # Verify retrieved preset
    retrieved = manager.get_preset("cyber_sunset")
    assert retrieved is not None
    assert retrieved.name == "Cyber Sunset"
    assert retrieved.colors.primary == "#ff5500"
    assert retrieved.typography.font_family == "JetBrains Mono"
    assert retrieved.border_radius == 8

    # Simulate PlasmaForge application restart with a fresh manager instance
    reloaded_manager = ThemePresetManager(storage_dir=tmp_path)
    assert len(reloaded_manager.list_presets()) == initial_count + 1
    reloaded_preset = reloaded_manager.get_preset("cyber_sunset")
    assert reloaded_preset is not None
    assert reloaded_preset.colors.primary == "#ff5500"
    assert reloaded_preset.is_builtin is False


def test_preset_manager_overwrite_and_deletion(tmp_path: Path) -> None:
    manager = ThemePresetManager(storage_dir=tmp_path)
    preset = ThemePreset(
        id="slate_custom",
        name="Slate Custom",
        colors=ThemeColors(primary="#3b82f6"),
    )
    ok, _ = manager.save_preset(preset)
    assert ok is True

    # Attempt overwrite without overwrite=True
    ok_dup, msg_dup = manager.save_preset(preset, overwrite=False)
    assert ok_dup is False
    assert "already exists" in msg_dup

    # Overwrite with overwrite=True
    preset.colors.primary = "#6366f1"
    ok_ow, msg_ow = manager.save_preset(preset, overwrite=True)
    assert ok_ow is True
    assert manager.get_preset("slate_custom").colors.primary == "#6366f1"

    # Cannot delete built-in presets
    ok_del_bi, _ = manager.delete_preset("plasmaforge_teal")
    assert ok_del_bi is False

    # Delete user preset
    ok_del, _ = manager.delete_preset("slate_custom")
    assert ok_del is True
    assert manager.get_preset("slate_custom") is None
    assert not (tmp_path / "slate_custom.json").exists()


def test_preset_manager_malformed_and_incompatible_files(tmp_path: Path) -> None:
    manager = ThemePresetManager(storage_dir=tmp_path)

    # Corrupt JSON file
    (tmp_path / "corrupt.json").write_text("{not valid json syntax", encoding="utf-8")

    # Incompatible schema version file
    (tmp_path / "incompatible.json").write_text(
        '{"schema_version": 999, "id": "future", "name": "Future Theme"}',
        encoding="utf-8",
    )

    # Oversized file
    oversized_data = "x" * (300 * 1024)
    (tmp_path / "oversized.json").write_text(f'{{"padding": "{oversized_data}"}}', encoding="utf-8")

    # Manager should gracefully skip invalid files without raising an exception
    presets = manager.list_presets()
    preset_ids = [p.id for p in presets]
    assert "future" not in preset_ids
    assert "corrupt" not in preset_ids
    assert "oversized" not in preset_ids
    assert len(presets) >= 4  # Builtins remain intact


def test_preset_import_and_export(tmp_path: Path) -> None:
    manager = ThemePresetManager(storage_dir=tmp_path)

    # Export
    export_path = tmp_path / "exported_nordic.json"
    ok_exp, _ = manager.export_preset("nordic_horizon", export_path)
    assert ok_exp is True
    assert export_path.is_file()

    # Import file
    import_target_dir = tmp_path / "imported_storage"
    import_manager = ThemePresetManager(storage_dir=import_target_dir)
    ok_imp, msg_imp, imported = import_manager.import_preset_file(export_path)
    assert ok_imp is True
    assert imported is not None
    # ID collided with built-in, so imported suffix assigned
    assert "imported" in imported.id.lower() or imported.id == "nordic_horizon"
    assert imported.colors.primary == "#88c0d0"

    # Import raw JSON string
    raw_json = """{
        "schema_version": 1,
        "id": "raw_imported",
        "name": "Raw Imported",
        "colors": {
            "primary": "#e11d48",
            "background": "#0f172a",
            "surface": "#1e293b",
            "text": "#f8fafc",
            "secondary_text": "#94a3b8"
        },
        "typography": {"font_family": "Noto Sans", "font_size": 12},
        "border_radius": 4,
        "spacing_scale": 0.85
    }"""
    ok_raw, _, raw_preset = import_manager.import_preset_json(raw_json)
    assert ok_raw is True
    assert raw_preset is not None
    assert raw_preset.name == "Raw Imported"
    assert raw_preset.colors.primary == "#e11d48"


def test_theme_controller_reactive_editing(tmp_path: Path, qapp: QGuiApplication) -> None:
    ctrl = ThemeController(storage_dir=tmp_path)

    # Initial default values
    assert ctrl.primaryColor == "#14b8a6"
    assert ctrl.backgroundColor == "#131518"
    assert ctrl.surfaceColor == "#181b20"
    assert ctrl.textColor == "#f3f4f6"
    assert ctrl.secondaryTextColor == "#9ca3af"
    assert ctrl.fontFamily == "Inter"
    assert ctrl.fontSize == 13
    assert ctrl.borderRadius == 6
    assert ctrl.spacingScale == 1.0
    assert ctrl.isDraftModified is False

    signals_emitted = []
    ctrl.themeDraftChanged.connect(lambda: signals_emitted.append(True))

    # Edit color
    ctrl.setPrimaryColor("#3b82f6")
    assert ctrl.primaryColor == "#3b82f6"
    assert ctrl.isDraftModified is True
    assert len(signals_emitted) >= 1

    ctrl.setBackgroundColor("#0a0c10")
    assert ctrl.backgroundColor == "#0a0c10"

    ctrl.setSurfaceColor("#1f2228")
    assert ctrl.surfaceColor == "#1f2228"

    ctrl.setTextColor("#ffffff")
    assert ctrl.textColor == "#ffffff"

    ctrl.setSecondaryTextColor("#6b7280")
    assert ctrl.secondaryTextColor == "#6b7280"

    # Edit typography
    ctrl.setFontFamily("JetBrains Mono")
    assert ctrl.fontFamily == "JetBrains Mono"

    ctrl.setFontSize(16)
    assert ctrl.fontSize == 16

    # Edit radius and spacing scale
    ctrl.setBorderRadius(12)
    assert ctrl.borderRadius == 12
    assert ctrl.radiusSm == 10
    assert ctrl.radiusMd == 12
    assert ctrl.radiusLg == 14
    assert ctrl.radiusXl == 18

    ctrl.setSpacingScale(1.25)
    assert ctrl.spacingScale == 1.25
    assert ctrl.spacingXs >= 4
    assert ctrl.spacingSm >= 8
    assert ctrl.spacingMd >= 14

    # Invalid input guards
    ctrl.setPrimaryColor("not-a-hex")
    assert ctrl.primaryColor == "#3b82f6"  # Preserved

    ctrl.setFontSize(999)
    assert ctrl.fontSize == 24  # Clamped to upper bound

    ctrl.setBorderRadius(-5)
    assert ctrl.borderRadius == 0  # Clamped to lower bound


def test_theme_controller_preset_workflows(tmp_path: Path, qapp: QGuiApplication) -> None:
    ctrl = ThemeController(storage_dir=tmp_path)

    # 1. Load an existing preset
    assert ctrl.loadPreset("nordic_horizon") is True
    assert ctrl.currentPresetId == "nordic_horizon"
    assert ctrl.primaryColor == "#88c0d0"
    assert ctrl.isDraftModified is False

    # 2. Modify draft
    ctrl.setPrimaryColor("#f43f5e")
    assert ctrl.isDraftModified is True

    # 3. Save as named user preset
    save_dialog_events = []
    ctrl.presetDialogStateChanged.connect(lambda: save_dialog_events.append(True))

    ctrl.requestSavePreset()
    assert ctrl.showPresetSaveDialog is True
    assert ctrl.presetSaveDialogMode == "save_new"

    ctrl.cancelSavePreset()
    assert ctrl.showPresetSaveDialog is False

    # Confirm save new
    assert ctrl.confirmSavePreset("Rose Nordic", overwrite=False) is True
    assert ctrl.showPresetSaveDialog is False
    assert ctrl.currentPresetId == "rose_nordic"
    assert ctrl.currentPresetName == "Rose Nordic"
    assert ctrl.isDraftModified is False
    assert ctrl.isCurrentPresetBuiltin is False

    # 4. Overwrite workflow
    ctrl.setPrimaryColor("#e11d48")
    assert ctrl.isDraftModified is True
    ctrl.requestOverwritePreset("rose_nordic")
    assert ctrl.showPresetSaveDialog is True
    assert ctrl.presetSaveDialogMode == "overwrite"

    assert ctrl.confirmSavePreset("Rose Nordic", overwrite=True) is True
    assert ctrl.primaryColor == "#e11d48"
    assert ctrl.isDraftModified is False

    # 5. Delete workflow
    ctrl.requestDeletePreset("rose_nordic")
    assert ctrl.showPresetDeleteDialog is True
    assert ctrl.deleteTargetPresetId == "rose_nordic"
    assert ctrl.deleteTargetPresetName == "Rose Nordic"

    ctrl.cancelDeletePreset()
    assert ctrl.showPresetDeleteDialog is False

    ctrl.requestDeletePreset("rose_nordic")
    assert ctrl.confirmDeletePreset() is True
    assert ctrl.showPresetDeleteDialog is False
    # After deleting active preset, should restore default
    assert ctrl.currentPresetId == "plasmaforge_teal"

    # 6. Restore default theme
    ctrl.setPrimaryColor("#ff0000")
    ctrl.restoreDefaultTheme()
    assert ctrl.primaryColor == "#14b8a6"
    assert ctrl.currentPresetId == "plasmaforge_teal"
