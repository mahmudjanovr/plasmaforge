"""Tests for safe system and KDE Plasma 6 environment inspection."""

from pathlib import Path

from plasmaforge.core.system_info import (
    get_system_info,
    read_kdeglobals_info,
    detect_plasma_version,
)


def test_read_kdeglobals_info_custom(tmp_path: Path) -> None:
    fake_kdeglobals = tmp_path / "kdeglobals"
    content = """
[General]
font=Inter,10,-1,5,400,0,0,0,0,0,0,0,0,0,0,1
fixed=JetBrains Mono,10,-1,5,400,0,0,0,0,0,0,0,0,0,0,1

[KDE]
LookAndFeelPackage=org.kde.breezedark.desktop
"""
    fake_kdeglobals.write_text(content, encoding="utf-8")

    laf, font, fixed = read_kdeglobals_info(fake_kdeglobals)
    assert laf == "org.kde.breezedark.desktop"
    assert font == "Inter"
    assert fixed == "JetBrains Mono"


def test_read_kdeglobals_nonexistent() -> None:
    laf, font, fixed = read_kdeglobals_info(Path("/nonexistent/kdeglobals"))
    assert "Breeze Dark" in laf
    assert "System" in font
    assert "Monospace" in fixed


def test_get_system_info() -> None:
    info = get_system_info()
    assert info.session_type in {"wayland", "x11", "tty"}
    assert info.safe_mode_active is True
    assert isinstance(info.tools_available, dict)
    assert "plasmashell" in info.tools_available
    assert "plasma-apply-colorscheme" in info.tools_available
    assert info.qt_version != ""
    assert isinstance(info.to_dict(), dict)
