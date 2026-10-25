"""Tests for color theme extraction and gallery preset bundles."""

from plasmaforge.core.themes import _rgb_to_hex, ThemeInspector
from plasmaforge.core.presets import get_all_presets


def test_rgb_to_hex() -> None:
    assert _rgb_to_hex("32,35,38") == "#202326"
    assert _rgb_to_hex("255,255,255") == "#ffffff"
    assert _rgb_to_hex("0,0,0") == "#000000"
    assert _rgb_to_hex("invalid", default="#14b8a6") == "#14b8a6"
    assert _rgb_to_hex("", default="#121212") == "#121212"


def test_theme_inspector_discovery() -> None:
    inspector = ThemeInspector()
    schemes = inspector.get_color_schemes()
    assert isinstance(schemes, list)
    if schemes:
        first = schemes[0]
        assert first.name != ""
        assert first.window_bg.startswith("#")
        assert first.selection_bg.startswith("#")

    styles = inspector.get_plasma_styles()
    assert isinstance(styles, list)


def test_curated_presets() -> None:
    presets = get_all_presets()
    assert len(presets) >= 4
    for p in presets:
        assert p.id != ""
        assert p.title != ""
        assert len(p.tags) > 0
        assert "bg" in p.preview_colors
        assert "accent" in p.preview_colors
        cs = p.to_changeset()
        errors = cs.validate()
        assert len(errors) == 0, f"Preset {p.id} had validation errors: {errors}"
