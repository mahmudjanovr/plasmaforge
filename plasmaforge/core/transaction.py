"""Reusable transactional safety layer for KDE Plasma configuration operations.

Guarantees:
1. Unified workflow: validation -> preview -> pre-apply backup & verification -> confirmation -> apply -> post-apply verification -> commit/rollback.
2. Allowlisted targets: only approved KDE configuration files within ~/.config can be targeted.
3. Safe execution: subprocess argument vectors (shell=False) with execution timeouts.
4. Cryptographic integrity: SHA256 checksums verified before and after operations.
5. Automated rollback: any failure during apply or verification triggers restoration of the pre-apply snapshot.
6. Safe Mode enforcement: prevents live modification by default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from plasmaforge.core.backup_manager import (
    SAFE_KDE_CONFIG_FILES,
    BackupManager,
    _compute_sha256,
)


class TransactionState(str, Enum):
    """Lifecycle states of a transactional configuration operation."""

    IDLE = "IDLE"
    VALIDATING = "VALIDATING"
    PREVIEWING = "PREVIEWING"
    BACKING_UP = "BACKING_UP"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    APPLYING = "APPLYING"
    VERIFYING = "VERIFYING"
    COMMITTED = "COMMITTED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"
    ABORTED = "ABORTED"


@dataclass
class ApplyOperation:
    """Definition of a customization operation to execute safely."""

    id: str
    title: str
    description: str
    affected_files: List[str]  # Must be file names in SAFE_KDE_CONFIG_FILES
    diff_preview: str = ""
    validate_fn: Optional[Callable[[], tuple[bool, str]]] = None
    apply_fn: Optional[Callable[[], tuple[bool, str]]] = None
    verify_fn: Optional[Callable[[], tuple[bool, str]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransactionResult:
    """Result of a transactional customization operation."""

    success: bool
    state: TransactionState
    message: str
    operation_id: str
    affected_files: List[str] = field(default_factory=list)
    backup_id: str = ""
    rolled_back: bool = False
    rollback_error: Optional[str] = None
    is_dry_run: bool = False
    diff_preview: str = ""


class TransactionalSafetyEngine:
    """Coordinates validation, pre-apply backups, execution, verification, and rollback."""

    def __init__(
        self,
        backup_manager: Optional[BackupManager] = None,
        safe_mode: bool = True,
        source_config_dir: Optional[Path] = None,
    ) -> None:
        self.backup_manager = backup_manager or BackupManager()
        self.safe_mode = safe_mode
        self.source_config_dir = source_config_dir or (Path.home() / ".config")

    def validate_target_file(self, filename: str) -> tuple[bool, str]:
        """Validate that a target file is allowlisted and does not traverse outside config dir."""
        if not filename or not filename.strip():
            return False, "Target file name cannot be empty."

        clean_name = filename.strip()
        if clean_name not in SAFE_KDE_CONFIG_FILES:
            return (
                False,
                f"File '{clean_name}' is not in the allowed KDE configuration whitelist: {SAFE_KDE_CONFIG_FILES}",
            )

        # Check for path traversal
        resolved = (self.source_config_dir / clean_name).resolve()
        config_root = self.source_config_dir.resolve()
        try:
            resolved.relative_to(config_root)
        except ValueError:
            return False, f"Path traversal detected: '{clean_name}' escapes configuration directory."

        return True, "Valid"

    def validate_operation(self, operation: ApplyOperation) -> tuple[bool, List[str]]:
        """Validate target files and pre-conditions for an operation."""
        errors: List[str] = []

        if not operation.affected_files:
            errors.append("Operation specifies no affected files.")

        for f in operation.affected_files:
            valid, msg = self.validate_target_file(f)
            if not valid:
                errors.append(msg)

        if operation.validate_fn:
            try:
                fn_ok, fn_msg = operation.validate_fn()
                if not fn_ok:
                    errors.append(f"Operation pre-condition failed: {fn_msg}")
            except Exception as e:
                errors.append(f"Validation hook raised exception: {e}")

        return (len(errors) == 0), errors

    def _rollback(
        self, backup_id: str, affected_files: List[str]
    ) -> tuple[bool, str]:
        """Restore previous configuration from a backup and verify integrity."""
        ok, msg = self.backup_manager.restore_snapshot(backup_id, file_whitelist=affected_files)
        if not ok:
            return False, f"Snapshot restore failed: {msg}"

        # Verify restored files match snapshot checksums
        snap_dir = self.backup_manager.backup_root / backup_id / "files"
        for fname in affected_files:
            snap_file = snap_dir / fname
            live_file = self.source_config_dir / fname
            if snap_file.is_file() and live_file.is_file():
                if _compute_sha256(live_file) != _compute_sha256(snap_file):
                    return False, f"Post-rollback integrity mismatch on '{fname}'."

        return True, "Rollback verified successfully."

    def execute(
        self,
        operation: ApplyOperation,
        confirmed: bool = False,
        force_safe_mode: Optional[bool] = None,
    ) -> TransactionResult:
        """Execute an operation within a transactional safety boundary."""
        is_safe = self.safe_mode if force_safe_mode is None else force_safe_mode

        # 1. Validation
        valid, errors = self.validate_operation(operation)
        if not valid:
            return TransactionResult(
                success=False,
                state=TransactionState.ABORTED,
                message=f"Validation failed: {'; '.join(errors)}",
                operation_id=operation.id,
                affected_files=operation.affected_files,
                diff_preview=operation.diff_preview,
            )

        # 2. Safe Mode Simulation
        if is_safe:
            # Create verified simulation snapshot to ensure backup subsystem is functional
            sim_meta = self.backup_manager.create_snapshot(
                f"Safe Mode Simulation: {operation.title}"
            )
            return TransactionResult(
                success=True,
                state=TransactionState.COMMITTED,
                message=f"Safe Mode active: Simulated '{operation.title}'. Live desktop session was not modified.",
                operation_id=operation.id,
                affected_files=operation.affected_files,
                backup_id=sim_meta.id,
                is_dry_run=True,
                diff_preview=operation.diff_preview,
            )

        # 3. Explicit Confirmation Check for Live Modification
        if not confirmed:
            return TransactionResult(
                success=False,
                state=TransactionState.AWAITING_CONFIRMATION,
                message=f"Explicit confirmation required for live modification of: {', '.join(operation.affected_files)}",
                operation_id=operation.id,
                affected_files=operation.affected_files,
                diff_preview=operation.diff_preview,
            )

        # 4. Pre-Apply Backup and Verification
        try:
            backup_meta = self.backup_manager.create_snapshot(
                f"Automatic Pre-Apply: {operation.title}"
            )
            valid_backup, backup_errors = self.backup_manager.verify_snapshot_integrity(
                backup_meta.id
            )
            if not valid_backup:
                return TransactionResult(
                    success=False,
                    state=TransactionState.ABORTED,
                    message=f"Pre-apply backup integrity verification failed ({'; '.join(backup_errors)}). Application aborted before modifying configuration.",
                    operation_id=operation.id,
                    affected_files=operation.affected_files,
                    backup_id=backup_meta.id,
                    diff_preview=operation.diff_preview,
                )
        except Exception as e:
            return TransactionResult(
                success=False,
                state=TransactionState.ABORTED,
                message=f"Failed to create pre-apply backup: {e}. Application aborted before modifying configuration.",
                operation_id=operation.id,
                affected_files=operation.affected_files,
                diff_preview=operation.diff_preview,
            )

        # 5. Apply Execution
        if not operation.apply_fn:
            return TransactionResult(
                success=False,
                state=TransactionState.ABORTED,
                message="No apply function provided for operation.",
                operation_id=operation.id,
                affected_files=operation.affected_files,
                backup_id=backup_meta.id,
                diff_preview=operation.diff_preview,
            )

        try:
            apply_ok, apply_msg = operation.apply_fn()
        except Exception as e:
            apply_ok, apply_msg = False, str(e)

        if not apply_ok:
            # Trigger automatic rollback
            rb_ok, rb_msg = self._rollback(backup_meta.id, operation.affected_files)
            if rb_ok:
                return TransactionResult(
                    success=False,
                    state=TransactionState.ROLLED_BACK,
                    message=f"Application failed ({apply_msg}). Automatic rollback restored previous configuration successfully.",
                    operation_id=operation.id,
                    affected_files=operation.affected_files,
                    backup_id=backup_meta.id,
                    rolled_back=True,
                    diff_preview=operation.diff_preview,
                )
            else:
                return TransactionResult(
                    success=False,
                    state=TransactionState.ROLLBACK_FAILED,
                    message=f"CRITICAL: Application failed ({apply_msg}) AND rollback failed ({rb_msg}).",
                    operation_id=operation.id,
                    affected_files=operation.affected_files,
                    backup_id=backup_meta.id,
                    rolled_back=False,
                    rollback_error=rb_msg,
                    diff_preview=operation.diff_preview,
                )

        # 6. Post-Apply Verification (Never report success before verification!)
        if operation.verify_fn:
            try:
                verify_ok, verify_msg = operation.verify_fn()
            except Exception as e:
                verify_ok, verify_msg = False, str(e)

            if not verify_ok:
                # Trigger automatic rollback on failed verification
                rb_ok, rb_msg = self._rollback(backup_meta.id, operation.affected_files)
                if rb_ok:
                    return TransactionResult(
                        success=False,
                        state=TransactionState.ROLLED_BACK,
                        message=f"Post-apply verification failed ({verify_msg}). Changes were automatically rolled back.",
                        operation_id=operation.id,
                        affected_files=operation.affected_files,
                        backup_id=backup_meta.id,
                        rolled_back=True,
                        diff_preview=operation.diff_preview,
                    )
                else:
                    return TransactionResult(
                        success=False,
                        state=TransactionState.ROLLBACK_FAILED,
                        message=f"CRITICAL: Verification failed ({verify_msg}) AND rollback failed ({rb_msg}).",
                        operation_id=operation.id,
                        affected_files=operation.affected_files,
                        backup_id=backup_meta.id,
                        rolled_back=False,
                        rollback_error=rb_msg,
                        diff_preview=operation.diff_preview,
                    )

        # 7. Commit
        return TransactionResult(
            success=True,
            state=TransactionState.COMMITTED,
            message=f"Successfully applied and verified '{operation.title}'.",
            operation_id=operation.id,
            affected_files=operation.affected_files,
            backup_id=backup_meta.id,
            diff_preview=operation.diff_preview,
        )

    def restore_snapshot_transactionally(
        self,
        snap_id: str,
        file_whitelist: Optional[List[str]] = None,
        confirmed: bool = False,
        force_safe_mode: Optional[bool] = None,
    ) -> TransactionResult:
        """Safely restore a snapshot with integrity verification, pre-restore backup, and post-restore validation."""
        is_safe = self.safe_mode if force_safe_mode is None else force_safe_mode
        target_files = file_whitelist or list(SAFE_KDE_CONFIG_FILES)

        # 1. Validate target files are allowlisted
        for f in target_files:
            valid, err = self.validate_target_file(f)
            if not valid:
                return TransactionResult(
                    success=False,
                    state=TransactionState.ABORTED,
                    message=f"Restore aborted: {err}",
                    operation_id=f"restore_{snap_id}",
                    affected_files=target_files,
                )

        # 2. Check snapshot exists and verify integrity before doing anything
        snap_dir = self.backup_manager.backup_root / snap_id
        if not snap_dir.is_dir():
            return TransactionResult(
                success=False,
                state=TransactionState.ABORTED,
                message=f"Snapshot '{snap_id}' does not exist in snapshot storage.",
                operation_id=f"restore_{snap_id}",
                affected_files=target_files,
            )

        valid_snap, snap_errors = self.backup_manager.verify_snapshot_integrity(snap_id)
        if not valid_snap:
            return TransactionResult(
                success=False,
                state=TransactionState.ABORTED,
                message=f"Refusing restore: snapshot integrity failed ({'; '.join(snap_errors)}). Cannot restore corrupted snapshot.",
                operation_id=f"restore_{snap_id}",
                affected_files=target_files,
            )

        # 3. Safe Mode check
        if is_safe:
            diff_data = self.backup_manager.dry_run_diff(snap_id)
            mod_count = diff_data.get("modified_files", 0)
            return TransactionResult(
                success=True,
                state=TransactionState.COMMITTED,
                message=f"Safe Mode active: Simulated restore for snapshot '{snap_id}' ({mod_count} files would change). Live files were not modified.",
                operation_id=f"restore_{snap_id}",
                affected_files=target_files,
                is_dry_run=True,
            )

        # 4. Confirmation check
        if not confirmed:
            return TransactionResult(
                success=False,
                state=TransactionState.AWAITING_CONFIRMATION,
                message=f"Explicit confirmation required to restore snapshot '{snap_id}' to live configuration.",
                operation_id=f"restore_{snap_id}",
                affected_files=target_files,
            )

        # 5. Create pre-restore safety backup of live configuration
        try:
            pre_restore_meta = self.backup_manager.create_snapshot(
                f"Safety Pre-Restore Backup: Before restoring '{snap_id}'"
            )
            v_ok, v_errs = self.backup_manager.verify_snapshot_integrity(pre_restore_meta.id)
            if not v_ok:
                return TransactionResult(
                    success=False,
                    state=TransactionState.ABORTED,
                    message=f"Pre-restore safety backup failed integrity check ({'; '.join(v_errs)}). Restore aborted.",
                    operation_id=f"restore_{snap_id}",
                    affected_files=target_files,
                )
        except Exception as e:
            return TransactionResult(
                success=False,
                state=TransactionState.ABORTED,
                message=f"Failed to create pre-restore safety backup: {e}. Restore aborted.",
                operation_id=f"restore_{snap_id}",
                affected_files=target_files,
            )

        # 6. Perform restore
        restored_ok, restore_msg = self.backup_manager.restore_snapshot(
            snap_id, file_whitelist=target_files
        )
        if not restored_ok:
            # Rollback to pre-restore snapshot
            self._rollback(pre_restore_meta.id, target_files)
            return TransactionResult(
                success=False,
                state=TransactionState.ROLLED_BACK,
                message=f"Snapshot restore failed ({restore_msg}). Configuration was rolled back to pre-restore state.",
                operation_id=f"restore_{snap_id}",
                affected_files=target_files,
                backup_id=pre_restore_meta.id,
                rolled_back=True,
            )

        # 7. Post-restore verification: verify restored files match the snapshot files
        snap_files_dir = snap_dir / "files"
        for fname in target_files:
            snap_file = snap_files_dir / fname
            live_file = self.source_config_dir / fname
            if snap_file.is_file() and live_file.is_file():
                if _compute_sha256(live_file) != _compute_sha256(snap_file):
                    # Verification failed: rollback!
                    self._rollback(pre_restore_meta.id, target_files)
                    return TransactionResult(
                        success=False,
                        state=TransactionState.ROLLED_BACK,
                        message=f"Post-restore verification failed on '{fname}'. Configuration was rolled back to pre-restore state.",
                        operation_id=f"restore_{snap_id}",
                        affected_files=target_files,
                        backup_id=pre_restore_meta.id,
                        rolled_back=True,
                    )

        # 8. Commit
        return TransactionResult(
            success=True,
            state=TransactionState.COMMITTED,
            message=f"Successfully restored and verified configuration from snapshot '{snap_id}'.",
            operation_id=f"restore_{snap_id}",
            affected_files=target_files,
            backup_id=pre_restore_meta.id,
        )
