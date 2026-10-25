"""Tests for KDE Plasma 6 color scheme application, validation, backup, and rollback."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from plasmaforge.core.backup_manager import BackupManager
from plasmaforge.core.color_scheme_applier import (
    ApplyResult,
    KdeColorSchemeApplier,
)
from plasmaforge.core.themes import detect_active_color_scheme


@pytest.fixture
def mock_env(tmp_path: Path):
    """Setup isolated mock KDE environment."""
    source_dir = tmp_path / "config"
    source_dir.mkdir()
    kdeglobals = source_dir / "kdeglobals"
    kdeglobals.write_text(
        "[General]\nColorScheme=BreezeDark\n\n[Colors:Window]\nBackgroundNormal=32,35,38\n",
        encoding="utf-8",
    )

    scheme_dir = tmp_path / "color-schemes"
    scheme_dir.mkdir()
    test_scheme = scheme_dir / "TestNordic.colors"
    test_scheme.write_text(
        "[General]\nName=Test Nordic\n\n[Colors:Window]\nBackgroundNormal=46,52,64\n\n[Colors:Selection]\nBackgroundNormal=136,192,208\n",
        encoding="utf-8",
    )

    backup_dir = tmp_path / "snapshots"
    bm = BackupManager(backup_root=backup_dir, source_config_dir=source_dir)

    applier = KdeColorSchemeApplier(
        backup_manager=bm,
        safe_mode=True,
        source_config_dir=source_dir,
        tool_binary="/usr/bin/plasma-apply-colorscheme",
    )
    applier.scheme_dirs = [scheme_dir]

    return {
        "applier": applier,
        "backup_manager": bm,
        "source_dir": source_dir,
        "kdeglobals": kdeglobals,
        "scheme_dir": scheme_dir,
        "backup_dir": backup_dir,
    }


def test_scheme_validation(mock_env):
    applier = mock_env["applier"]

    # Valid scheme
    valid, path, err = applier.validate_scheme("TestNordic")
    assert valid is True
    assert path.is_file()
    assert err == "Valid"

    # Empty scheme ID
    valid, _, err = applier.validate_scheme("")
    assert valid is False
    assert "empty" in err.lower()

    # Injection characters
    valid, _, err = applier.validate_scheme("Test; rm -rf /")
    assert valid is False
    assert "forbidden characters" in err

    # Non-existent scheme
    valid, _, err = applier.validate_scheme("DoesntExist")
    assert valid is False
    assert "not found" in err


def test_generate_diff_preview(mock_env):
    applier = mock_env["applier"]
    diff = applier.generate_diff_preview("TestNordic")
    assert "Unified Diff Preview: Color Scheme 'TestNordic'" in diff
    assert "Target: " in diff
    assert "+BackgroundNormal" in diff


def test_safe_mode_prevents_real_execution(mock_env):
    applier = mock_env["applier"]
    applier.safe_mode = True

    with patch.object(applier, "_execute_apply_command") as mock_exec:
        result = applier.apply_scheme("TestNordic")
        # Subprocess should never be called in Safe Mode
        mock_exec.assert_not_called()

        assert result.success is True
        assert result.is_dry_run is True
        assert "Safe Mode active" in result.message
        assert result.backup_id != ""
        assert "Unified Diff Preview" in result.diff_preview


def test_live_mode_success_with_backup(mock_env):
    applier = mock_env["applier"]
    applier.safe_mode = False

    def fake_exec(tool, scheme_id):
        # Simulate real plasma-apply-colorscheme updating kdeglobals
        mock_env["kdeglobals"].write_text(
            f"[General]\nColorScheme={scheme_id}\n\n[Colors:Window]\nBackgroundNormal=46,52,64\n",
            encoding="utf-8",
        )
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch.object(applier, "_execute_apply_command", side_effect=fake_exec) as mock_exec:
        result = applier.apply_scheme("TestNordic")

        # Subprocess must be called with exact argument vector, NO shell
        mock_exec.assert_called_once_with(
            "/usr/bin/plasma-apply-colorscheme", "TestNordic"
        )

        assert result.success is True
        assert result.is_dry_run is False
        assert result.backup_id != ""
        assert result.rolled_back is False

        # Verify pre-apply backup was created and intact
        valid, errors = mock_env["backup_manager"].verify_snapshot_integrity(
            result.backup_id
        )
        assert valid is True
        assert len(errors) == 0


def test_live_mode_verification_failure_triggers_automatic_rollback(mock_env):
    applier = mock_env["applier"]
    applier.safe_mode = False
    kdeglobals = mock_env["kdeglobals"]
    original_text = kdeglobals.read_text(encoding="utf-8")

    # Simulate tool returning 0 without actually updating General.ColorScheme
    def fake_exec_noop(tool, scheme_id):
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch.object(applier, "_execute_apply_command", side_effect=fake_exec_noop):
        result = applier.apply_scheme("TestNordic")

        assert result.success is False
        assert "Verification failed" in result.message
        assert result.rolled_back is True
        assert result.backup_id != ""

        # Verify kdeglobals was restored to original content
        assert kdeglobals.read_text(encoding="utf-8") == original_text


def test_xdg_data_dirs_discovery(tmp_path: Path, monkeypatch):
    custom_xdg = tmp_path / "custom_share"
    custom_schemes = custom_xdg / "color-schemes"
    custom_schemes.mkdir(parents=True)
    (custom_schemes / "CustomXdg.colors").write_text("[General]\nName=Custom XDG\n", encoding="utf-8")

    monkeypatch.setenv("XDG_DATA_HOME", str(custom_xdg))
    applier = KdeColorSchemeApplier(source_config_dir=tmp_path)

    found = applier.find_scheme_file("CustomXdg")
    assert found is not None
    assert found.name == "CustomXdg.colors"


def test_live_mode_failure_triggers_automatic_rollback(mock_env):
    applier = mock_env["applier"]
    applier.safe_mode = False
    kdeglobals = mock_env["kdeglobals"]
    original_text = kdeglobals.read_text(encoding="utf-8")

    with patch.object(applier, "_execute_apply_command") as mock_exec:
        # Simulate KDE tool failure
        mock_exec.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="plasma-apply-colorscheme: error applying scheme",
        )

        result = applier.apply_scheme("TestNordic")

        assert result.success is False
        assert "KDE color scheme application failed" in result.message
        assert result.rolled_back is True
        assert result.backup_id != ""

        # Verify kdeglobals was restored to original content
        current_text = kdeglobals.read_text(encoding="utf-8")
        assert current_text == original_text


def test_restore_backup(mock_env):
    applier = mock_env["applier"]
    bm = mock_env["backup_manager"]
    kdeglobals = mock_env["kdeglobals"]

    # Create backup with original content
    kdeglobals.write_text("[OriginalState]\nKey=Value\n", encoding="utf-8")
    meta = bm.create_snapshot("Before Mutation")

    # Mutate kdeglobals
    kdeglobals.write_text("[MutatedState]\nKey=Changed\n", encoding="utf-8")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        ok, msg = applier.restore_backup(meta.id, target_scheme_id="TestNordic")

        assert ok is True
        assert "Successfully restored" in msg
        assert kdeglobals.read_text(encoding="utf-8") == "[OriginalState]\nKey=Value\n"


def test_detect_active_color_scheme():
    # Detect against live system
    active = detect_active_color_scheme()
    assert isinstance(active, str)
    assert len(active) > 0
