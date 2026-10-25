"""Backup controller coordinating snapshot creation, integrity checks, dry-run diffs, and safe transactional restore."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from plasmaforge.core.backup_manager import BackupManager, SnapshotMetadata
from plasmaforge.core.config import get_config
from plasmaforge.core.transaction import (
    TransactionalSafetyEngine,
    TransactionResult,
    TransactionState,
)


class BackupController(QObject):
    """Exposes snapshot creation, listing, integrity verification, dry-run diffs, and safe restore to QML."""

    snapshotsChanged = Signal()
    selectedSnapshotChanged = Signal()
    diffReportChanged = Signal()
    integrityStatusChanged = Signal()
    snapshotOperationCompleted = Signal(str, bool)  # message, success
    restoreConfirmDialogChanged = Signal()
    isRestoringChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._manager = BackupManager()
        self._safety_engine = TransactionalSafetyEngine(
            backup_manager=self._manager,
            safe_mode=get_config().safe_mode,
        )
        self._snapshots: List[Dict[str, Any]] = []
        self._selected_id = ""
        self._selected_snapshot: Dict[str, Any] = {}
        self._diff_report = ""
        self._integrity_status = ""

        # Restore modal state
        self._show_restore_confirm_dialog = False
        self._is_restoring = False
        self._restore_target_id = ""
        self._restore_target_description = ""
        self._restore_target_file_count = 0

        self.refreshSnapshots()

    @Slot()
    def refreshSnapshots(self) -> None:
        raw_snapshots = self._manager.list_snapshots()
        self._snapshots = [s.to_dict() for s in raw_snapshots]
        self.snapshotsChanged.emit()

        if self._snapshots:
            if not any(s["id"] == self._selected_id for s in self._snapshots):
                self.selectSnapshot(self._snapshots[0]["id"])
            else:
                # Refresh selected snapshot dict and diff
                for s in self._snapshots:
                    if s["id"] == self._selected_id:
                        self._selected_snapshot = s
                        self.selectedSnapshotChanged.emit()
                        break
        else:
            self._selected_id = ""
            self._selected_snapshot = {}
            self._diff_report = ""
            self._integrity_status = ""
            self.selectedSnapshotChanged.emit()
            self.diffReportChanged.emit()
            self.integrityStatusChanged.emit()

    @Property("QVariantList", notify=snapshotsChanged)
    def snapshots(self) -> List[Dict[str, Any]]:
        return self._snapshots

    @Property(int, notify=snapshotsChanged)
    def snapshotCount(self) -> int:
        return len(self._snapshots)

    @Property(str, notify=selectedSnapshotChanged)
    def selectedSnapshotId(self) -> str:
        return self._selected_id

    @Property("QVariantMap", notify=selectedSnapshotChanged)
    def selectedSnapshot(self) -> Dict[str, Any]:
        return self._selected_snapshot

    @Property(str, notify=diffReportChanged)
    def diffReport(self) -> str:
        return self._diff_report

    @Property(str, notify=integrityStatusChanged)
    def integrityStatus(self) -> str:
        return self._integrity_status

    @Property(bool, notify=restoreConfirmDialogChanged)
    def showRestoreConfirmDialog(self) -> bool:
        return self._show_restore_confirm_dialog

    @Property(bool, notify=isRestoringChanged)
    def isRestoring(self) -> bool:
        return self._is_restoring

    @Property(str, notify=restoreConfirmDialogChanged)
    def restoreTargetSnapshotId(self) -> str:
        return self._restore_target_id

    @Property(str, notify=restoreConfirmDialogChanged)
    def restoreTargetDescription(self) -> str:
        return self._restore_target_description

    @Property(int, notify=restoreConfirmDialogChanged)
    def restoreTargetFileCount(self) -> int:
        return self._restore_target_file_count

    @Slot(str)
    def selectSnapshot(self, snap_id: str) -> None:
        for s in self._snapshots:
            if s["id"] == snap_id:
                self._selected_id = snap_id
                self._selected_snapshot = s
                self.selectedSnapshotChanged.emit()
                self.dryRunRestore(snap_id)
                self.verifySnapshot(snap_id)
                break

    @Slot(str, result=bool)
    def createSnapshot(self, description: str) -> bool:
        try:
            desc = description.strip() if description.strip() else "Manual Safe Snapshot"
            meta = self._manager.create_snapshot(desc)
            self.refreshSnapshots()
            self.selectSnapshot(meta.id)
            self.snapshotOperationCompleted.emit(
                f"Snapshot '{meta.id}' created safely ({meta.file_count} config files backed up).",
                True,
            )
            return True
        except Exception as e:
            self.snapshotOperationCompleted.emit(f"Failed to create snapshot: {e}", False)
            return False

    @Slot(str)
    def verifySnapshot(self, snap_id: str) -> None:
        valid, errors = self._manager.verify_snapshot_integrity(snap_id)
        if valid:
            self._integrity_status = "All files verified intact (SHA256 checksums match manifest)."
        else:
            self._integrity_status = "Integrity check issues:\n" + "\n".join(errors)
        self.integrityStatusChanged.emit()

    @Slot(str)
    def dryRunRestore(self, snap_id: str) -> None:
        diff_data = self._manager.dry_run_diff(snap_id)
        if "error" in diff_data:
            self._diff_report = str(diff_data["error"])
        else:
            lines = [
                f"# Dry-Run Comparison with Live Configuration",
                f"# Snapshot ID: {snap_id}",
                f"# Identical files: {diff_data.get('identical_files', 0)}",
                f"# Modified files: {diff_data.get('modified_files', 0)}",
                f"# Missing in live: {diff_data.get('missing_in_live', 0)}",
                "--------------------------------------------------",
            ]
            file_diffs: dict = diff_data.get("file_diffs", {})
            for fname, info in file_diffs.items():
                status = info.get("status", "")
                diff_text = info.get("diff", "")
                lines.append(f"\nFile: {fname} [{status.upper()}]")
                if diff_text:
                    lines.append(diff_text)
                else:
                    lines.append("  (No differences detected with current live config)")

            self._diff_report = "\n".join(lines)

        self.diffReportChanged.emit()

    @Slot(str)
    def requestRestoreSnapshot(self, snap_id: str) -> None:
        """Initiate restore workflow. In Safe Mode simulates restore; in Live Mode requests explicit confirmation."""
        target_id = snap_id.strip() if snap_id.strip() else self._selected_id
        if not target_id:
            self.snapshotOperationCompleted.emit("No snapshot selected for restore.", False)
            return

        config = get_config()
        self._safety_engine.safe_mode = config.safe_mode

        # If in Safe Mode, perform dry-run simulation
        if config.safe_mode:
            res = self._safety_engine.restore_snapshot_transactionally(
                snap_id=target_id,
                confirmed=False,
                force_safe_mode=True,
            )
            self.snapshotOperationCompleted.emit(res.message, res.success)
            self.dryRunRestore(target_id)
            return

        # If in Live Mode, find details and open confirmation dialog
        self._restore_target_id = target_id
        for s in self._snapshots:
            if s["id"] == target_id:
                self._restore_target_description = s.get("description", "Safe Snapshot")
                self._restore_target_file_count = s.get("file_count", 0)
                break
        else:
            self._restore_target_description = "Safe Snapshot"
            self._restore_target_file_count = 0

        self._show_restore_confirm_dialog = True
        self.restoreConfirmDialogChanged.emit()

    @Slot()
    def cancelRestore(self) -> None:
        """Cancel confirmation dialog."""
        self._show_restore_confirm_dialog = False
        self.restoreConfirmDialogChanged.emit()

    @Slot(result=bool)
    def confirmRestore(self) -> bool:
        """Confirm and execute live snapshot restoration with pre-restore backup and post-restore verification."""
        self._show_restore_confirm_dialog = False
        self.restoreConfirmDialogChanged.emit()

        if not self._restore_target_id:
            self.snapshotOperationCompleted.emit("No snapshot target specified.", False)
            return False

        return self.restoreSnapshot(self._restore_target_id, force_safe_mode=False)

    @Slot(str, result=bool)
    def restoreSnapshot(self, snap_id: str, force_safe_mode: Optional[bool] = None) -> bool:
        """Directly restore a snapshot within the transactional safety boundary."""
        config = get_config()
        self._safety_engine.safe_mode = config.safe_mode
        self._is_restoring = True
        self.isRestoringChanged.emit()

        try:
            res: TransactionResult = self._safety_engine.restore_snapshot_transactionally(
                snap_id=snap_id,
                confirmed=True,
                force_safe_mode=force_safe_mode,
            )
            self._is_restoring = False
            self.isRestoringChanged.emit()

            self.snapshotOperationCompleted.emit(res.message, res.success)
            if res.success:
                self.refreshSnapshots()
                self.dryRunRestore(snap_id)
            return res.success
        except Exception as e:
            self._is_restoring = False
            self.isRestoringChanged.emit()
            self.snapshotOperationCompleted.emit(f"Restore failed with unexpected error: {e}", False)
            return False
