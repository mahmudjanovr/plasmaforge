"""Safe snapshot and rollback engine for KDE Plasma configuration files.

Creates versioned, cryptographic-integrity-verified snapshots of KDE
configuration files to an isolated storage directory. Enforces safe, non-destructive
dry-run checks before any potential future restoration.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from plasmaforge.core.system_info import detect_plasma_version


# Standard KDE configuration files that define the desktop environment state
SAFE_KDE_CONFIG_FILES = [
    "kdeglobals",
    "plasmarc",
    "plasma-org.kde.plasma.desktop-appletsrc",
    "kwinrc",
    "kglobalshortcutsrc",
    "kcminputrc",
]

# Strict snapshot ID pattern: letters, numbers, underscores, and dashes only
SAFE_SNAPSHOT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")


    
@dataclass
class FileEntry:
    """Metadata for an individual snapshot file."""

    name: str
    sha256: str
    size_bytes: int


@dataclass
class SnapshotMetadata:
    """Metadata for a complete snapshot bundle."""

    id: str
    created_at: str
    description: str
    plasma_version: str
    file_count: int
    total_size_bytes: int
    files: List[FileEntry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        d = asdict(self)
        d["files"] = [asdict(f) for f in self.files]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> SnapshotMetadata:
        raw_files = data.get("files", [])
        files = [
            FileEntry(
                name=f["name"],
                sha256=f["sha256"],
                size_bytes=f["size_bytes"],
            )
            for f in raw_files
        ]
        return cls(
            id=str(data["id"]),
            created_at=str(data["created_at"]),
            description=str(data.get("description", "")),
            plasma_version=str(data.get("plasma_version", "6.x")),
            file_count=int(data.get("file_count", len(files))),
            total_size_bytes=int(data.get("total_size_bytes", 0)),
            files=files,
        )


def _compute_sha256(path: Path) -> str:
    """Compute sha256 checksum of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class BackupManager:
    """Safe manager for creating, inspecting, and verifying KDE config snapshots."""

    def __init__(
        self,
        backup_root: Optional[Path] = None,
        source_config_dir: Optional[Path] = None,
    ) -> None:
        self.backup_root = backup_root or (
            Path.home() / ".local" / "share" / "plasmaforge" / "snapshots"
        )
        self.source_config_dir = source_config_dir or (Path.home() / ".config")
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, description: str = "Manual Safe Snapshot") -> SnapshotMetadata:
        """Create a sandboxed copy of existing KDE config files with cryptographic manifest."""
        now = datetime.now(timezone.utc)
        base_id = f"snap_{now.strftime('%Y%m%d_%H%M%S')}"
        snap_id = base_id
        counter = 1
        while (self.backup_root / snap_id).exists():
            snap_id = f"{base_id}_{counter}"
            counter += 1

        snap_dir = self.backup_root / snap_id
        files_dir = snap_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)

        copied_entries: List[FileEntry] = []
        total_size = 0

        for filename in SAFE_KDE_CONFIG_FILES:
            src = self.source_config_dir / filename
            if src.is_file():
                dest = files_dir / filename
                # Safe copy preserving permissions
                shutil.copy2(src, dest)
                sha = _compute_sha256(dest)
                size = dest.stat().st_size
                total_size += size
                copied_entries.append(
                    FileEntry(name=filename, sha256=sha, size_bytes=size)
                )

        metadata = SnapshotMetadata(
            id=snap_id,
            created_at=now.isoformat(),
            description=description,
            plasma_version=detect_plasma_version(),
            file_count=len(copied_entries),
            total_size_bytes=total_size,
            files=copied_entries,
        )

        manifest_path = snap_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        return metadata

    def is_valid_snapshot_id(self, snap_id: str) -> bool:
        """Validate that a snapshot ID contains only safe alphanumeric/underscore/dash characters."""
        if not snap_id or not isinstance(snap_id, str):
            return False
        clean = snap_id.strip()
        if not clean or len(clean) > 128:
            return False
        if not SAFE_SNAPSHOT_ID_REGEX.match(clean):
            return False
        if ".." in clean or "/" in clean or "\\" in clean:
            return False
        return True

    def get_snapshot_path(self, snap_id: str) -> tuple[bool, Path, str]:
        """Validate and resolve a snapshot directory strictly inside backup_root."""
        if not self.is_valid_snapshot_id(snap_id):
            return False, Path(), f"Invalid snapshot identifier '{snap_id}'."

        clean = snap_id.strip()
        target = self.backup_root / clean
        try:
            resolved_target = target.resolve()
            resolved_root = self.backup_root.resolve()
        except Exception as e:
            return False, Path(), f"Failed to resolve path: {e}"

        # Path traversal guard: must be strictly within backup_root
        try:
            resolved_target.relative_to(resolved_root)
        except ValueError:
            return False, Path(), f"Security violation: path traversal detected for '{snap_id}'."

        if resolved_target == resolved_root:
            return False, Path(), "Security violation: target is the root snapshot directory."

        return True, resolved_target, ""

    def delete_snapshot(
        self, snap_id: str, protected_ids: Optional[Set[str]] = None
    ) -> tuple[bool, str]:
        """Safely delete a snapshot folder and its contents.

        Guarantees:
        1. Validates snap_id format and strictly rejects path traversal attempts.
        2. Ensures the target path is strictly inside backup_root.
        3. Protects active transaction snapshots from deletion if protected_ids is specified.
        4. Verifies the directory exists and contains manifest.json before deletion.
        5. Deletes completely and reports failure cleanly if filesystem operations error.
        """
        valid_id, target_dir, err = self.get_snapshot_path(snap_id)
        if not valid_id:
            return False, err

        if protected_ids and snap_id in protected_ids:
            return False, f"Cannot delete snapshot '{snap_id}': it is protected by an active transaction."

        if not target_dir.is_dir():
            return False, f"Snapshot '{snap_id}' does not exist on disk."

        manifest_path = target_dir / "manifest.json"
        if not manifest_path.is_file():
            return False, f"Refusing to delete: snapshot '{snap_id}' is missing a valid manifest file."

        try:
            shutil.rmtree(target_dir)
            if target_dir.exists():
                return False, f"Failed to completely remove snapshot directory '{snap_id}'."
            return True, f"Snapshot '{snap_id}' deleted successfully."
        except Exception as e:
            return False, f"Error deleting snapshot '{snap_id}': {e}"

    def delete_snapshots(
        self, snap_ids: List[str], protected_ids: Optional[Set[str]] = None
    ) -> tuple[int, List[str]]:
        """Safely delete multiple snapshots, returning count of deleted and list of error messages."""
        deleted_count = 0
        errors: List[str] = []
        for sid in snap_ids:
            ok, msg = self.delete_snapshot(sid, protected_ids=protected_ids)
            if ok:
                deleted_count += 1
            else:
                errors.append(msg)
        return deleted_count, errors

    def list_snapshots(self) -> List[SnapshotMetadata]:
        """List all valid snapshots in the backup directory, sorted newest first."""
        if not self.backup_root.is_dir():
            return []

        results: List[SnapshotMetadata] = []
        for snap_dir in sorted(self.backup_root.iterdir(), reverse=True):
            if not snap_dir.is_dir():
                continue
            manifest = snap_dir / "manifest.json"
            if manifest.is_file():
                try:
                    with open(manifest, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        results.append(SnapshotMetadata.from_dict(data))
                except Exception:
                    continue

        # Sort predictably newest first by ISO created_at timestamp, then id
        results.sort(key=lambda s: (s.created_at, s.id), reverse=True)
        return results

    def verify_snapshot_integrity(self, snap_id: str) -> tuple[bool, List[str]]:
        """Verify that all files in a snapshot match their original SHA256 hashes."""
        valid_id, snap_dir, err = self.get_snapshot_path(snap_id)
        if not valid_id:
            return False, [err]

        manifest_path = snap_dir / "manifest.json"
        if not manifest_path.is_file():
            return False, ["Manifest file missing."]


        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                metadata = SnapshotMetadata.from_dict(data)
        except Exception as e:
            return False, [f"Manifest corrupted: {e}"]

        errors: List[str] = []
        files_dir = snap_dir / "files"
        for entry in metadata.files:
            file_path = files_dir / entry.name
            if not file_path.is_file():
                errors.append(f"Snapshot file missing: {entry.name}")
                continue
            actual_sha = _compute_sha256(file_path)
            if actual_sha != entry.sha256:
                errors.append(
                    f"Integrity check failed for {entry.name}: hash mismatch."
                )

        return (len(errors) == 0), errors

    def dry_run_diff(self, snap_id: str) -> Dict[str, object]:
        """Compute differences between snapshot and current live configuration without writing anything."""
        valid_id, snap_dir, err = self.get_snapshot_path(snap_id)
        if not valid_id:
            return {"error": err}

        manifest_path = snap_dir / "manifest.json"
        if not manifest_path.is_file():
            return {"error": f"Snapshot {snap_id} not found."}

        with open(manifest_path, "r", encoding="utf-8") as f:
            metadata = SnapshotMetadata.from_dict(json.load(f))

        diff_summary: Dict[str, object] = {
            "snapshot_id": snap_id,
            "created_at": metadata.created_at,
            "description": metadata.description,
            "identical_files": 0,
            "modified_files": 0,
            "missing_in_live": 0,
            "file_diffs": {},
        }

        files_dir = snap_dir / "files"
        for entry in metadata.files:
            snap_file = files_dir / entry.name
            live_file = self.source_config_dir / entry.name

            if not snap_file.is_file():
                continue

            snap_text = snap_file.read_text(encoding="utf-8", errors="replace")

            if not live_file.is_file():
                diff_summary["missing_in_live"] += 1
                diff_summary["file_diffs"][entry.name] = {
                    "status": "missing_in_live",
                    "diff": f"File {entry.name} does not exist in live environment.",
                }
                continue

            live_text = live_file.read_text(encoding="utf-8", errors="replace")

            if snap_text == live_text:
                diff_summary["identical_files"] += 1
                diff_summary["file_diffs"][entry.name] = {
                    "status": "identical",
                    "diff": "",
                }
            else:
                diff_summary["modified_files"] += 1
                udiff = list(
                    difflib.unified_diff(
                        live_text.splitlines(keepends=True),
                        snap_text.splitlines(keepends=True),
                        fromfile=f"live/{entry.name}",
                        tofile=f"snapshot/{entry.name}",
                        n=2,
                    )
                )
                diff_summary["file_diffs"][entry.name] = {
                    "status": "modified",
                    "diff": "".join(udiff[:40]),  # Cap diff preview for UI display
                }

        return diff_summary

    def restore_snapshot(
        self, snap_id: str, file_whitelist: Optional[List[str]] = None
    ) -> tuple[bool, str]:
        """Safely restore KDE configuration files from a verified snapshot."""
        valid_id, snap_dir, err = self.get_snapshot_path(snap_id)
        if not valid_id:
            return False, err

        if not snap_dir.is_dir():
            return False, f"Snapshot '{snap_id}' does not exist."


        # Verify integrity before attempting restore
        valid, errors = self.verify_snapshot_integrity(snap_id)
        if not valid:
            return False, f"Refusing restore: snapshot integrity failed ({'; '.join(errors)})"

        manifest_path = snap_dir / "manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            metadata = SnapshotMetadata.from_dict(json.load(f))

        files_dir = snap_dir / "files"
        restored_count = 0
        allowed = set(SAFE_KDE_CONFIG_FILES)
        if file_whitelist:
            allowed = allowed.intersection(set(file_whitelist))

        for entry in metadata.files:
            if entry.name not in allowed:
                continue

            snap_file = files_dir / entry.name
            if not snap_file.is_file():
                continue

            dest = self.source_config_dir / entry.name
            self.source_config_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(snap_file, dest)
            restored_count += 1

        if restored_count == 0:
            return False, "No matching configuration files found to restore."

        return True, f"Successfully restored {restored_count} configuration files from {snap_id}."

