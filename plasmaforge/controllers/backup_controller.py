"""Backup controller coordinating snapshot creation, integrity checks, and dry-run restore."""

from __future__ import annotations

from typing import Any, Dict, List

from PySide6.QtCore import Property, QObject, Signal, Slot

from plasmaforge.core.backup_manager import BackupManager, SnapshotMetadata
from plasmaforge.core.config import get_config


class BackupController(QObject):
    """Exposes snapshot creation, listing, integrity verification and dry-run diffs to QML."""

    snapshotsChanged = Signal()
    selectedSnapshotChanged = Signal()
    diffReportChanged = Signal()
    integrityStatusChanged = Signal()
    snapshotOperationCompleted = Signal(str, bool)  # message, success

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        config = get_config()
        self._manager = BackupManager()
        self._snapshots: List[Dict[str, Any]] = []
        self._selected_id = ""
        self._selected_snapshot: Dict[str, Any] = {}
        self._diff_report = ""
        self._integrity_status = ""
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

    @Slot(str)
    def selectSnapshot(self, snap_id: str) -> None:
        for s in self._snapshots:
            if s["id"] == snap_id:
                self._selected_id = snap_id
                self._selected_snapshot = s
                self.selectedSnapshotChanged.emit()
                # Run dry run diff automatically for selection
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
