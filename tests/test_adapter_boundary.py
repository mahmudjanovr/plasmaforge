"""Tests for safety boundaries and adapter contracts."""

from pathlib import Path
import pytest

from plasmaforge.core.adapter_boundary import (
    ConfigChange,
    ConfigChangeSet,
    DryRunAdapter,
    SandboxAdapter,
    SafetyViolationError,
)


def test_valid_config_change() -> None:
    change = ConfigChange(
        file_identifier="kdeglobals",
        group="KDE",
        key="LookAndFeelPackage",
        new_value="org.kde.breezedark.desktop",
    )
    errors = change.validate()
    assert len(errors) == 0


def test_reject_unwhitelisted_file() -> None:
    change = ConfigChange(
        file_identifier="shadow",
        group="root",
        key="password",
        new_value="none",
    )
    errors = change.validate()
    assert any("whitelist" in e for e in errors)


def test_reject_newline_injection() -> None:
    change = ConfigChange(
        file_identifier="kdeglobals",
        group="General",
        key="font",
        new_value="Inter\n[MaliciousGroup]\nhacked=true",
    )
    errors = change.validate()
    assert any("newline" in e for e in errors)


def test_dry_run_adapter_preview_and_protection() -> None:
    change = ConfigChange(
        file_identifier="kdeglobals",
        group="KDE",
        key="LookAndFeelPackage",
        new_value="org.kde.breezedark.desktop",
        old_value="Nothing",
    )
    cs = ConfigChangeSet(
        name="Test Theme",
        description="Dry-run preview test",
        changes=[change],
    )

    adapter = DryRunAdapter(safe_mode=True)
    preview = adapter.preview(cs)
    assert "Dry-Run Preview: Test Theme" in preview
    assert "Target File: ~/.config/kdeglobals" in preview
    assert "+ LookAndFeelPackage = org.kde.breezedark.desktop" in preview

    # Applying in safe mode must raise SafetyViolationError
    with pytest.raises(SafetyViolationError) as exc:
        adapter.apply(cs)
    assert "Phase 1 Safety Mode Active" in str(exc.value)


def test_sandbox_adapter_isolated_execution(tmp_path: Path) -> None:
    sandbox_dir = tmp_path / "sandbox"
    adapter = SandboxAdapter(sandbox_root=sandbox_dir)

    change = ConfigChange(
        file_identifier="kdeglobals",
        group="KDE",
        key="LookAndFeelPackage",
        new_value="org.kde.breezedark.desktop",
    )
    cs = ConfigChangeSet(name="Sandbox Set", description="Test", changes=[change])

    success = adapter.apply(cs)
    assert success is True

    written_file = sandbox_dir / "kdeglobals"
    assert written_file.is_file()
    content = written_file.read_text(encoding="utf-8")
    assert "[KDE]" in content
    assert "LookAndFeelPackage = org.kde.breezedark.desktop" in content
