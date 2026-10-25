"""Tests for BackupManager snapshot creation, integrity checks, and dry-run diffs."""

from pathlib import Path

from plasmaforge.core.backup_manager import BackupManager


def test_create_and_list_snapshot(tmp_path: Path) -> None:
    source_dir = tmp_path / "mock_config"
    source_dir.mkdir()
    (source_dir / "kdeglobals").write_text("[KDE]\nLookAndFeelPackage=breezedark\n")
    (source_dir / "plasmarc").write_text("[Theme]\nname=default\n")

    backup_dir = tmp_path / "snapshots"
    bm = BackupManager(backup_root=backup_dir, source_config_dir=source_dir)

    meta = bm.create_snapshot("Initial Test Snapshot")
    assert meta.file_count == 2
    assert meta.description == "Initial Test Snapshot"
    assert len(meta.files) == 2

    # Check disk structure
    snap_dir = backup_dir / meta.id
    assert snap_dir.is_dir()
    assert (snap_dir / "manifest.json").is_file()
    assert (snap_dir / "files" / "kdeglobals").is_file()
    assert (snap_dir / "files" / "plasmarc").is_file()

    # List snapshots
    snaps = bm.list_snapshots()
    assert len(snaps) == 1
    assert snaps[0].id == meta.id


def test_snapshot_integrity_verification(tmp_path: Path) -> None:
    source_dir = tmp_path / "mock_config"
    source_dir.mkdir()
    (source_dir / "kdeglobals").write_text("[General]\nfont=Inter\n")

    backup_dir = tmp_path / "snapshots"
    bm = BackupManager(backup_root=backup_dir, source_config_dir=source_dir)

    meta = bm.create_snapshot("Integrity Check Snapshot")
    valid, errors = bm.verify_snapshot_integrity(meta.id)
    assert valid is True
    assert len(errors) == 0

    # Tamper with snapshot file
    snap_file = backup_dir / meta.id / "files" / "kdeglobals"
    snap_file.write_text("[TamperedContent]\n")

    valid_tampered, errors_tampered = bm.verify_snapshot_integrity(meta.id)
    assert valid_tampered is False
    assert len(errors_tampered) == 1
    assert "Integrity check failed" in errors_tampered[0]


def test_dry_run_diff(tmp_path: Path) -> None:
    source_dir = tmp_path / "mock_config"
    source_dir.mkdir()
    (source_dir / "kdeglobals").write_text("[General]\nfont=Inter\n")

    backup_dir = tmp_path / "snapshots"
    bm = BackupManager(backup_root=backup_dir, source_config_dir=source_dir)

    meta = bm.create_snapshot("Diff Snapshot")

    # Identical state
    diff1 = bm.dry_run_diff(meta.id)
    assert diff1["identical_files"] == 1
    assert diff1["modified_files"] == 0

    # Mutate live config
    (source_dir / "kdeglobals").write_text("[General]\nfont=Noto Sans\n")
    diff2 = bm.dry_run_diff(meta.id)
    assert diff2["identical_files"] == 0
    assert diff2["modified_files"] == 1
    assert "modified" == diff2["file_diffs"]["kdeglobals"]["status"]
