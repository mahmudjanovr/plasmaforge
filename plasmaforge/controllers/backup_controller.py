"""Backup controller coordinating snapshot creation, integrity checks, dry-run diffs, deletion, and safe transactional restore."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from PySide6.QtCore import Property, QObject, Signal, Slot

from plasmaforge.core.backup_manager import BackupManager, SnapshotMetadata
from plasmaforge.core.config import get_config
from plasmaforge.core.transaction import (
    TransactionalSafetyEngine,
    TransactionResult,
    TransactionState,
)


class BackupController(QObject):
    """Exposes snapshot creation, listing, integrity verification, dry-run diffs, safe deletion, and restore to QML."""

    snapshotsChanged = Signal()
    selectedSnapshotChanged = Signal()
    diffReportChanged = Signal()
    integrityStatusChanged = Signal()
    snapshotOperationCompleted = Signal(str, bool)  # message, success
    restoreConfirmDialogChanged = Signal()
    isRestoringChanged = Signal()
    deleteConfirmDialogChanged = Signal()
    isDeletingChanged = Signal()
    searchQueryChanged = Signal()

    def __init__(self, parent: QObject | None = None, backup_manager: Optional[BackupManager] = None) -> None:
        super().__init__(parent)
        self._manager = backup_manager or BackupManager()
        self._safety_engine = TransactionalSafetyEngine(
            backup_manager=self._manager,
            safe_mode=get_config().safe_mode,
        )
        self._snapshots: List[Dict[str, Any]] = []
        self._selected_id = ""
        self._selected_snapshot: Dict[str, Any] = {}
        self._diff_report = ""
        self._integrity_status = ""
        self._search_query = ""
        self._protected_snapshot_ids: Set[str] = set()

        # Restore modal state
        self._show_restore_confirm_dialog = False
        self._is_restoring = False
        self._restore_target_id = ""
        self._restore_target_description = ""
        self._restore_target_file_count = 0

        # Delete modal state
        self._show_delete_confirm_dialog = False
        self._is_deleting = False
        self._delete_target_id = ""
        self._delete_target_description = ""
        self._delete_target_created_at = ""
        self._delete_target_file_count = 0
        self._delete_target_size_kb = 0

        self.refreshSnapshots()

    @Slot()
    def refreshSnapshots(self) -> None:
        """Reload snapshots from disk and maintain deterministic selection."""
        raw_snapshots = self._manager.list_snapshots()
        self._snapshots = [s.to_dict() for s in raw_snapshots]
        self.snapshotsChanged.emit()

        filtered = self.snapshots
        if filtered:
            if not any(s["id"] == self._selected_id for s in filtered):
                self.selectSnapshot(filtered[0]["id"])
            else:
                # Refresh selected snapshot dict and dry-run diff
                for s in filtered:
                    if s["id"] == self._selected_id:
                        self._selected_snapshot = s
                        self.selectedSnapshotChanged.emit()
                        break
        elif self._snapshots:
            # Filtered list is empty, but snapshots exist
            self._selected_id = ""
            self._selected_snapshot = {}
            self._diff_report = "No snapshots match the current search filter."
            self._integrity_status = ""
            self.selectedSnapshotChanged.emit()
            self.diffReportChanged.emit()
            self.integrityStatusChanged.emit()
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
        """Return snapshots, filtered by search query if set."""
        if not self._search_query:
            return self._snapshots
        q = self._search_query.strip().lower()
        return [
            s
            for s in self._snapshots
            if q in s.get("id", "").lower()
            or q in s.get("description", "").lower()
            or q in s.get("created_at", "").lower()
        ]

    @Property(int, notify=snapshotsChanged)
    def snapshotCount(self) -> int:
        return len(self.snapshots)

    @Property(int, notify=snapshotsChanged)
    def totalSnapshotCount(self) -> int:
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

    @Property(str, notify=searchQueryChanged)
    def searchQuery(self) -> str:
        return self._search_query

    # Restore modal properties
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

    # Delete modal properties
    @Property(bool, notify=deleteConfirmDialogChanged)
    def showDeleteConfirmDialog(self) -> bool:
        return self._show_delete_confirm_dialog

    @Property(bool, notify=isDeletingChanged)
    def isDeleting(self) -> bool:
        return self._is_deleting

    @Property(str, notify=deleteConfirmDialogChanged)
    def deleteTargetSnapshotId(self) -> str:
        return self._delete_target_id

    @Property(str, notify=deleteConfirmDialogChanged)
    def deleteTargetDescription(self) -> str:
        return self._delete_target_description

    @Property(str, notify=deleteConfirmDialogChanged)
    def deleteTargetCreatedAt(self) -> str:
        return self._delete_target_created_at

    @Property(int, notify=deleteConfirmDialogChanged)
    def deleteTargetFileCount(self) -> int:
        return self._delete_target_file_count

    @Property(int, notify=deleteConfirmDialogChanged)
    def deleteTargetSizeKb(self) -> int:
        return self._delete_target_size_kb

    # Slots
    @Slot(str)
    def setSearchQuery(self, query: str) -> None:
        if self._search_query != query:
            self._search_query = query
            self.searchQueryChanged.emit()
            self.snapshotsChanged.emit()
            filtered = self.snapshots
            if filtered and not any(s["id"] == self._selected_id for s in filtered):
                self.selectSnapshot(filtered[0]["id"])
            elif not filtered:
                self._selected_id = ""
                self._selected_snapshot = {}
                self._diff_report = "No snapshots match the current search filter."
                self._integrity_status = ""
                self.selectedSnapshotChanged.emit()
                self.diffReportChanged.emit()
                self.integrityStatusChanged.emit()

    @Slot(str)
    def addProtectedSnapshotId(self, snap_id: str) -> None:
        """Register a snapshot ID as protected against deletion (e.g. active transaction snapshot)."""
        clean = snap_id.strip()
        if clean:
            self._protected_snapshot_ids.add(clean)

    @Slot(str)
    def removeProtectedSnapshotId(self, snap_id: str) -> None:
        """Remove a snapshot ID from the protected set."""
        clean = snap_id.strip()
        self._protected_snapshot_ids.discard(clean)

    @Slot(str)
    def selectSnapshot(self, snap_id: str) -> None:
        """Select a snapshot by ID and update diff preview and integrity status."""
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
        """Create a new snapshot and select it."""
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
        """Verify snapshot checksums against manifest."""
        valid, errors = self._manager.verify_snapshot_integrity(snap_id)
        if valid:
            self._integrity_status = "All files verified intact (SHA256 checksums match manifest)."
        else:
            self._integrity_status = "Integrity check issues:\n" + "\n".join(errors)
        self.integrityStatusChanged.emit()

    @Slot(str)
    def dryRunRestore(self, snap_id: str) -> None:
        """Compute dry-run diff against live configuration."""
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

    # Deletion workflow
    @Slot(str)
    def requestDeleteSnapshot(self, snap_id: str = "") -> None:
        """Open delete confirmation dialog identifying target snapshot."""
        target_id = snap_id.strip() if snap_id.strip() else self._selected_id
        if not target_id:
            self.snapshotOperationCompleted.emit("No snapshot selected for deletion.", False)
            return

        # Check if in progress
        if self._is_restoring or self._is_deleting:
            self.snapshotOperationCompleted.emit(
                "Cannot delete snapshot while another operation is in progress.", False
            )
            return

        # Check if protected
        if target_id in self._protected_snapshot_ids:
            self.snapshotOperationCompleted.emit(
                f"Cannot delete snapshot '{target_id}': it is protected by an active transaction.",
                False,
            )
            return

        # Lookup snapshot metadata for dialog
        self._delete_target_id = target_id
        for s in self._snapshots:
            if s["id"] == target_id:
                self._delete_target_description = s.get("description", "Safe Snapshot")
                self._delete_target_created_at = s.get("created_at", "")
                self._delete_target_file_count = s.get("file_count", 0)
                self._delete_target_size_kb = int(round(s.get("total_size_bytes", 0) / 1024))
                break
        else:
            self._delete_target_description = "Safe Snapshot"
            self._delete_target_created_at = ""
            self._delete_target_file_count = 0
            self._delete_target_size_kb = 0

        self._show_delete_confirm_dialog = True
        self.deleteConfirmDialogChanged.emit()

    @Slot()
    def cancelDelete(self) -> None:
        """Cancel delete confirmation dialog."""
        self._show_delete_confirm_dialog = False
        self._delete_target_id = ""
        self._delete_target_description = ""
        self._delete_target_created_at = ""
        self._delete_target_file_count = 0
        self._delete_target_size_kb = 0
        self.deleteConfirmDialogChanged.emit()

    @Slot(result=bool)
    def confirmDelete(self) -> bool:
        """Execute deletion of confirmed target snapshot."""
        self._show_delete_confirm_dialog = False
        self.deleteConfirmDialogChanged.emit()

        if not self._delete_target_id:
            self.snapshotOperationCompleted.emit("No snapshot specified for deletion.", False)
            return False

        target = self._delete_target_id
        self._delete_target_id = ""
        return self.deleteSnapshot(target)

    @Slot(str, result=bool)
    def deleteSnapshot(self, snap_id: str) -> bool:
        """Safely delete a snapshot, preserving consistent list ordering and selection state."""
        target_id = snap_id.strip() if snap_id.strip() else self._selected_id
        if not target_id:
            self.snapshotOperationCompleted.emit("No snapshot identifier provided.", False)
            return False

        if self._is_deleting or self._is_restoring:
            self.snapshotOperationCompleted.emit(
                "Cannot delete snapshot: another operation is currently in progress.", False
            )
            return False

        if target_id in self._protected_snapshot_ids:
            self.snapshotOperationCompleted.emit(
                f"Cannot delete snapshot '{target_id}': it is protected by an active transaction.",
                False,
            )
            return False

        if not self._manager.is_valid_snapshot_id(target_id):
            self.snapshotOperationCompleted.emit(
                f"Security check failed: invalid snapshot identifier '{target_id}'.", False
            )
            return False

        # Find current index before deletion to ensure seamless next selection
        current_idx = -1
        for idx, s in enumerate(self._snapshots):
            if s["id"] == target_id:
                current_idx = idx
                break

        self._is_deleting = True
        self.isDeletingChanged.emit()

        try:
            ok, msg = self._manager.delete_snapshot(
                target_id, protected_ids=self._protected_snapshot_ids
            )
        except Exception as e:
            ok, msg = False, f"Unexpected error during deletion: {e}"
        finally:
            self._is_deleting = False
            self.isDeletingChanged.emit()

        if not ok:
            self.snapshotOperationCompleted.emit(msg, False)
            return False

        # Reload snapshots from storage
        raw_snapshots = self._manager.list_snapshots()
        self._snapshots = [s.to_dict() for s in raw_snapshots]

        # Manage selection transition: if the deleted snapshot was selected, select adjacent
        if target_id == self._selected_id:
            if self._snapshots:
                new_idx = min(current_idx, len(self._snapshots) - 1) if current_idx >= 0 else 0
                new_id = self._snapshots[new_idx]["id"]
                self.selectSnapshot(new_id)
            else:
                self._selected_id = ""
                self._selected_snapshot = {}
                self._diff_report = "All snapshots deleted. Snapshot registry is empty."
                self._integrity_status = ""
                self.selectedSnapshotChanged.emit()
                self.diffReportChanged.emit()
                self.integrityStatusChanged.emit()
        else:
            # Refresh currently selected snapshot dict in case metadata changed
            for s in self._snapshots:
                if s["id"] == self._selected_id:
                    self._selected_snapshot = s
                    self.selectedSnapshotChanged.emit()
                    break

        self.snapshotsChanged.emit()
        self.snapshotOperationCompleted.emit(msg, True)
        return True

    @Slot("QVariantList", result=bool)
    def deleteMultipleSnapshots(self, snap_ids: List[str]) -> bool:
        """Batch delete multiple snapshots safely."""
        if not snap_ids:
            return True

        if self._is_deleting or self._is_restoring:
            self.snapshotOperationCompleted.emit(
                "Cannot delete snapshots: an operation is in progress.", False
            )
            return False

        self._is_deleting = True
        self.isDeletingChanged.emit()

        deleted_count = 0
        errors: List[str] = []

        try:
            for sid in snap_ids:
                if not self._manager.is_valid_snapshot_id(sid):
                    errors.append(f"Invalid ID '{sid}'")
                    continue
                if sid in self._protected_snapshot_ids:
                    errors.append(f"'{sid}' is protected")
                    continue
                ok, msg = self._manager.delete_snapshot(
                    sid, protected_ids=self._protected_snapshot_ids
                )
                if ok:
                    deleted_count += 1
                else:
                    errors.append(f"'{sid}': {msg}")
        finally:
            self._is_deleting = False
            self.isDeletingChanged.emit()

        self.refreshSnapshots()

        if errors:
            self.snapshotOperationCompleted.emit(
                f"Deleted {deleted_count} snapshots. Issues: {'; '.join(errors)}",
                deleted_count > 0,
            )
            return deleted_count > 0
        else:
            self.snapshotOperationCompleted.emit(
                f"Successfully deleted {deleted_count} snapshots.", True
            )
            return True

    # Restore workflow
    @Slot(str)
    def requestRestoreSnapshot(self, snap_id: str) -> None:
        """Initiate restore workflow. In Safe Mode simulates restore; in Live Mode requests explicit confirmation."""
        target_id = snap_id.strip() if snap_id.strip() else self._selected_id
        if not target_id:
            self.snapshotOperationCompleted.emit("No snapshot selected for restore.", False)
            return

        if self._is_deleting or self._is_restoring:
            self.snapshotOperationCompleted.emit(
                "Cannot restore: another operation is in progress.", False
            )
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

        target = self._restore_target_id
        self._restore_target_id = ""
        return self.restoreSnapshot(target, force_safe_mode=False)

    @Slot(str, result=bool)
    def restoreSnapshot(self, snap_id: str, force_safe_mode: Optional[bool] = None) -> bool:
        """Directly restore a snapshot within the transactional safety boundary."""
        config = get_config()
        self._safety_engine.safe_mode = config.safe_mode
        self._is_restoring = True
        self.isRestoringChanged.emit()

        # Protect target snapshot from deletion during restore
        self.addProtectedSnapshotId(snap_id)

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
        finally:
            self.removeProtectedSnapshotId(snap_id)
