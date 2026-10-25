"""Tests for the Phase 3 reusable transactional safety engine, rollback, and restore."""

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from plasmaforge.core.backup_manager import BackupManager, _compute_sha256
from plasmaforge.core.transaction import (
    ApplyOperation,
    TransactionalSafetyEngine,
    TransactionResult,
    TransactionState,
)
from plasmaforge.controllers.backup_controller import BackupController


@pytest.fixture
def mock_safety_env(tmp_path: Path):
    """Setup isolated config and snapshot directories for testing."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    kdeglobals = config_dir / "kdeglobals"
    kdeglobals.write_text("[General]\nColorScheme=BreezeDark\n", encoding="utf-8")

    plasmarc = config_dir / "plasmarc"
    plasmarc.write_text("[Theme]\nname=default\n", encoding="utf-8")

    backup_dir = tmp_path / "snapshots"
    bm = BackupManager(backup_root=backup_dir, source_config_dir=config_dir)

    engine = TransactionalSafetyEngine(
        backup_manager=bm,
        safe_mode=True,
        source_config_dir=config_dir,
    )

    return {
        "engine": engine,
        "backup_manager": bm,
        "config_dir": config_dir,
        "kdeglobals": kdeglobals,
        "plasmarc": plasmarc,
        "backup_dir": backup_dir,
    }


def test_transaction_success(mock_safety_env):
    """Happy path: validation -> backup & verify -> apply -> verify -> commit."""
    engine = mock_safety_env["engine"]
    kdeglobals = mock_safety_env["kdeglobals"]

    applied = False
    verified = False

    def do_apply():
        nonlocal applied
        applied = True
        kdeglobals.write_text("[General]\nColorScheme=TestScheme\n", encoding="utf-8")
        return True, "Success"

    def do_verify():
        nonlocal verified
        verified = True
        content = kdeglobals.read_text(encoding="utf-8")
        return ("ColorScheme=TestScheme" in content), "Verified"

    op = ApplyOperation(
        id="test_op_1",
        title="Test Scheme Apply",
        description="Applying a test scheme",
        affected_files=["kdeglobals"],
        diff_preview="--- diff ---",
        apply_fn=do_apply,
        verify_fn=do_verify,
    )

    result = engine.execute(op, confirmed=True, force_safe_mode=False)

    assert result.success is True
    assert result.state == TransactionState.COMMITTED
    assert result.rolled_back is False
    assert result.backup_id != ""
    assert applied is True
    assert verified is True

    # Check pre-apply backup integrity
    valid, errors = mock_safety_env["backup_manager"].verify_snapshot_integrity(result.backup_id)
    assert valid is True
    assert len(errors) == 0


def test_transaction_failed_application(mock_safety_env):
    """When apply_fn fails, automatic rollback restores previous configuration."""
    engine = mock_safety_env["engine"]
    kdeglobals = mock_safety_env["kdeglobals"]
    original_text = kdeglobals.read_text(encoding="utf-8")

    def failing_apply():
        # Mutate before crashing
        kdeglobals.write_text("[CorruptedState]\nBad=Data\n", encoding="utf-8")
        return False, "Simulated execution crash"

    op = ApplyOperation(
        id="test_fail_apply",
        title="Failing Apply Op",
        description="Testing failure rollback",
        affected_files=["kdeglobals"],
        apply_fn=failing_apply,
    )

    result = engine.execute(op, confirmed=True, force_safe_mode=False)

    assert result.success is False
    assert result.state == TransactionState.ROLLED_BACK
    assert result.rolled_back is True
    assert "Automatic rollback restored previous configuration successfully" in result.message

    # Verify original file content was restored
    assert kdeglobals.read_text(encoding="utf-8") == original_text


def test_transaction_failed_verification(mock_safety_env):
    """When apply succeeds but verify fails, operation is rolled back and reported as failure."""
    engine = mock_safety_env["engine"]
    kdeglobals = mock_safety_env["kdeglobals"]
    original_text = kdeglobals.read_text(encoding="utf-8")

    def buggy_apply():
        # Apply writes wrong key
        kdeglobals.write_text("[General]\nWrongKey=Value\n", encoding="utf-8")
        return True, "Executed"

    def strict_verify():
        content = kdeglobals.read_text(encoding="utf-8")
        if "ColorScheme=ExpectedScheme" in content:
            return True, "Verified"
        return False, "Expected key ColorScheme=ExpectedScheme missing from configuration"

    op = ApplyOperation(
        id="test_fail_verify",
        title="Failing Verify Op",
        description="Testing verification rollback",
        affected_files=["kdeglobals"],
        apply_fn=buggy_apply,
        verify_fn=strict_verify,
    )

    result = engine.execute(op, confirmed=True, force_safe_mode=False)

    assert result.success is False
    assert result.state == TransactionState.ROLLED_BACK
    assert result.rolled_back is True
    assert "Post-apply verification failed" in result.message

    # File must be restored to original
    assert kdeglobals.read_text(encoding="utf-8") == original_text


def test_transaction_backup_corruption(mock_safety_env):
    """If pre-apply backup integrity verification fails, operation aborts BEFORE apply."""
    engine = mock_safety_env["engine"]
    bm = mock_safety_env["backup_manager"]

    # Mock verify_snapshot_integrity to simulate pre-apply backup corruption
    bm.verify_snapshot_integrity = MagicMock(return_value=(False, ["Checksum mismatch on manifest"]))

    apply_called = False

    def should_not_run():
        nonlocal apply_called
        apply_called = True
        return True, "Applied"

    op = ApplyOperation(
        id="test_corrupt_backup",
        title="Corrupted Backup Test",
        description="Testing backup corruption abort",
        affected_files=["kdeglobals"],
        apply_fn=should_not_run,
    )

    result = engine.execute(op, confirmed=True, force_safe_mode=False)

    assert result.success is False
    assert result.state == TransactionState.ABORTED
    assert "Pre-apply backup integrity verification failed" in result.message
    assert apply_called is False


def test_transaction_rollback_failure(mock_safety_env):
    """If apply fails AND rollback fails, state is ROLLBACK_FAILED with alert details."""
    engine = mock_safety_env["engine"]
    bm = mock_safety_env["backup_manager"]

    def failing_apply():
        return False, "Tool crashed"

    # Mock restore_snapshot to fail
    bm.restore_snapshot = MagicMock(return_value=(False, "Disk full"))

    op = ApplyOperation(
        id="test_rollback_fail",
        title="Rollback Failure Op",
        description="Testing double failure",
        affected_files=["kdeglobals"],
        apply_fn=failing_apply,
    )

    result = engine.execute(op, confirmed=True, force_safe_mode=False)

    assert result.success is False
    assert result.state == TransactionState.ROLLBACK_FAILED
    assert result.rolled_back is False
    assert result.rollback_error is not None
    assert "Disk full" in result.rollback_error
    assert "CRITICAL:" in result.message


def test_transaction_safe_mode(mock_safety_env):
    """In Safe Mode, apply_fn is never called and dry-run result is returned."""
    engine = mock_safety_env["engine"]
    engine.safe_mode = True

    apply_called = False

    def do_apply():
        nonlocal apply_called
        apply_called = True
        return True, "Applied"

    op = ApplyOperation(
        id="test_safe_mode",
        title="Safe Mode Op",
        description="Testing safe mode protection",
        affected_files=["kdeglobals"],
        diff_preview="--- simulated diff ---",
        apply_fn=do_apply,
    )

    result = engine.execute(op, confirmed=True, force_safe_mode=True)

    assert result.success is True
    assert result.is_dry_run is True
    assert result.state == TransactionState.COMMITTED
    assert "Safe Mode active" in result.message
    assert apply_called is False


def test_transaction_unconfirmed_live_mode(mock_safety_env):
    """In Live Mode without confirmation, execution halts at AWAITING_CONFIRMATION."""
    engine = mock_safety_env["engine"]

    apply_called = False

    def do_apply():
        nonlocal apply_called
        apply_called = True
        return True, "Applied"

    op = ApplyOperation(
        id="test_unconfirmed",
        title="Unconfirmed Op",
        description="Testing confirmation requirement",
        affected_files=["kdeglobals"],
        apply_fn=do_apply,
    )

    result = engine.execute(op, confirmed=False, force_safe_mode=False)

    assert result.success is False
    assert result.state == TransactionState.AWAITING_CONFIRMATION
    assert "Explicit confirmation required" in result.message
    assert apply_called is False


def test_transaction_unsafe_target_rejection(mock_safety_env):
    """Operations targeting unallowlisted files or path traversals are rejected."""
    engine = mock_safety_env["engine"]

    # Arbitrary file outside whitelist
    op_bad_file = ApplyOperation(
        id="test_bad_file",
        title="Bad File Op",
        description="Targeting non-KDE file",
        affected_files=["not_a_kde_config.txt"],
    )
    res1 = engine.execute(op_bad_file, confirmed=True, force_safe_mode=False)
    assert res1.success is False
    assert res1.state == TransactionState.ABORTED
    assert "not in the allowed KDE configuration whitelist" in res1.message

    # Path traversal attack
    op_traversal = ApplyOperation(
        id="test_traversal",
        title="Traversal Op",
        description="Path traversal",
        affected_files=["../../etc/shadow"],
    )
    res2 = engine.execute(op_traversal, confirmed=True, force_safe_mode=False)
    assert res2.success is False
    assert res2.state == TransactionState.ABORTED


def test_transaction_restore_snapshot_success(mock_safety_env):
    """Manual snapshot restore: creates pre-restore backup, restores files, and verifies."""
    engine = mock_safety_env["engine"]
    bm = mock_safety_env["backup_manager"]
    kdeglobals = mock_safety_env["kdeglobals"]

    # Original state
    kdeglobals.write_text("[OriginalState]\nKey=1\n", encoding="utf-8")
    meta = bm.create_snapshot("Original Snapshot")

    # Mutate
    kdeglobals.write_text("[MutatedState]\nKey=2\n", encoding="utf-8")

    result = engine.restore_snapshot_transactionally(
        snap_id=meta.id,
        confirmed=True,
        force_safe_mode=False,
    )

    assert result.success is True
    assert result.state == TransactionState.COMMITTED
    assert kdeglobals.read_text(encoding="utf-8") == "[OriginalState]\nKey=1\n"
    assert result.backup_id != ""  # Pre-restore safety backup was created


def test_transaction_restore_snapshot_refuses_corrupted(mock_safety_env):
    """Refuses to restore a snapshot whose files or manifest are corrupted."""
    engine = mock_safety_env["engine"]
    bm = mock_safety_env["backup_manager"]
    kdeglobals = mock_safety_env["kdeglobals"]

    meta = bm.create_snapshot("Legit Snapshot")

    # Tamper with snapshot file
    snap_file = mock_safety_env["backup_dir"] / meta.id / "files" / "kdeglobals"
    snap_file.write_text("[TamperedContent]\nMalicious=True\n", encoding="utf-8")

    result = engine.restore_snapshot_transactionally(
        snap_id=meta.id,
        confirmed=True,
        force_safe_mode=False,
    )

    assert result.success is False
    assert result.state == TransactionState.ABORTED
    assert "Refusing restore: snapshot integrity failed" in result.message
    # Live config was not modified
    assert "[TamperedContent]" not in kdeglobals.read_text(encoding="utf-8")


def test_transaction_restore_snapshot_safe_mode(mock_safety_env):
    """In Safe Mode, restore returns dry-run simulation without modifying live files."""
    engine = mock_safety_env["engine"]
    bm = mock_safety_env["backup_manager"]
    kdeglobals = mock_safety_env["kdeglobals"]

    kdeglobals.write_text("[State1]\n", encoding="utf-8")
    meta = bm.create_snapshot("Snap1")

    kdeglobals.write_text("[State2]\n", encoding="utf-8")

    result = engine.restore_snapshot_transactionally(
        snap_id=meta.id,
        force_safe_mode=True,
    )

    assert result.success is True
    assert result.is_dry_run is True
    assert result.state == TransactionState.COMMITTED
    assert "Safe Mode active: Simulated restore" in result.message
    assert kdeglobals.read_text(encoding="utf-8") == "[State2]\n"


def test_backup_controller_restore_workflow(mock_safety_env, monkeypatch):
    """Verify BackupController restore slots, signals, and modal state transitions."""
    bm = mock_safety_env["backup_manager"]
    meta = bm.create_snapshot("Test Snap for Controller")

    ctrl = BackupController()
    ctrl._manager = bm
    ctrl._safety_engine.backup_manager = bm
    ctrl._safety_engine.source_config_dir = mock_safety_env["config_dir"]
    ctrl.refreshSnapshots()

    # 1. Test requestRestoreSnapshot in Safe Mode
    monkeypatch.setattr("plasmaforge.controllers.backup_controller.get_config", lambda: MagicMock(safe_mode=True))
    ctrl.requestRestoreSnapshot(meta.id)
    assert ctrl.showRestoreConfirmDialog is False

    # 2. Test requestRestoreSnapshot in Live Mode
    monkeypatch.setattr("plasmaforge.controllers.backup_controller.get_config", lambda: MagicMock(safe_mode=False))
    ctrl.requestRestoreSnapshot(meta.id)
    assert ctrl.showRestoreConfirmDialog is True
    assert ctrl.restoreTargetSnapshotId == meta.id
    assert ctrl.restoreTargetDescription == "Test Snap for Controller"

    # 3. Test cancelRestore
    ctrl.cancelRestore()
    assert ctrl.showRestoreConfirmDialog is False

    # 4. Test confirmRestore in Live Mode
    ctrl.requestRestoreSnapshot(meta.id)
    assert ctrl.showRestoreConfirmDialog is True
    ok = ctrl.confirmRestore()
    assert ok is True
    assert ctrl.showRestoreConfirmDialog is False
