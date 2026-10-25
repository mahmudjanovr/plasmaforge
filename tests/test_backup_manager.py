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


def test_delete_snapshot_and_path_traversal_guards(tmp_path: Path) -> None:
    source_dir = tmp_path / "mock_config"
    source_dir.mkdir()
    (source_dir / "kdeglobals").write_text("[General]\nfont=Inter\n")

    backup_dir = tmp_path / "snapshots"
    bm = BackupManager(backup_root=backup_dir, source_config_dir=source_dir)

    meta1 = bm.create_snapshot("Snapshot 1")
    meta2 = bm.create_snapshot("Snapshot 2")
    assert len(bm.list_snapshots()) == 2

    # Verify happy path deletion of snapshot 1
    snap1_dir = backup_dir / meta1.id
    assert snap1_dir.is_dir()
    ok, msg = bm.delete_snapshot(meta1.id)
    assert ok is True
    assert not snap1_dir.exists()
    assert len(bm.list_snapshots()) == 1
    assert bm.list_snapshots()[0].id == meta2.id

    # Test rejection of path traversal attempts
    traversal_ids = [
        "../etc",
        "../../root",
        "snap/subdir",
        "snap\\subdir",
        "",
        "..",
        ".",
        "snap id with spaces",
        "snap$illegal",
    ]
    for bad_id in traversal_ids:
        ok_bad, msg_bad = bm.delete_snapshot(bad_id)
        assert ok_bad is False
        assert "Invalid snapshot identifier" in msg_bad or "Path traversal" in msg_bad

    # Test non-existent snapshot
    ok_missing, msg_missing = bm.delete_snapshot("snap_nonexistent_12345")
    assert ok_missing is False
    assert "does not exist" in msg_missing or "not found" in msg_missing

    # Test directory without manifest.json
    fake_snap = backup_dir / "snap_fake_dir"
    fake_snap.mkdir()
    ok_fake, msg_fake = bm.delete_snapshot("snap_fake_dir")
    assert ok_fake is False
    assert "missing a valid manifest" in msg_fake or "manifest" in msg_fake


def test_delete_snapshot_protected_id(tmp_path: Path) -> None:
    source_dir = tmp_path / "mock_config"
    source_dir.mkdir()
    (source_dir / "kdeglobals").write_text("[General]\nfont=Inter\n")

    backup_dir = tmp_path / "snapshots"
    bm = BackupManager(backup_root=backup_dir, source_config_dir=source_dir)

    meta = bm.create_snapshot("Protected Snapshot")
    protected_set = {meta.id}

    # Attempt delete while protected
    ok, msg = bm.delete_snapshot(meta.id, protected_ids=protected_set)
    assert ok is False
    assert "protected" in msg
    assert (backup_dir / meta.id).exists()

    # Once unprotected, delete succeeds
    ok2, msg2 = bm.delete_snapshot(meta.id, protected_ids=set())
    assert ok2 is True
    assert not (backup_dir / meta.id).exists()


def test_delete_snapshots_batch(tmp_path: Path) -> None:
    source_dir = tmp_path / "mock_config"
    source_dir.mkdir()
    (source_dir / "kdeglobals").write_text("[General]\nfont=Inter\n")

    backup_dir = tmp_path / "snapshots"
    bm = BackupManager(backup_root=backup_dir, source_config_dir=source_dir)

    m1 = bm.create_snapshot("Batch 1")
    m2 = bm.create_snapshot("Batch 2")
    m3 = bm.create_snapshot("Batch 3")
    assert len(bm.list_snapshots()) == 3

    # Delete m1 and m2, but protect m2
    deleted_count, failed = bm.delete_snapshots([m1.id, m2.id], protected_ids={m2.id})
    assert deleted_count == 1
    assert len(failed) == 1
    assert m2.id in failed[0]
    assert "protected" in failed[0]
    assert len(bm.list_snapshots()) == 2
    remaining_ids = {s.id for s in bm.list_snapshots()}
    assert m1.id not in remaining_ids
    assert m2.id in remaining_ids
    assert m3.id in remaining_ids


def test_list_snapshots_sorted_descending(tmp_path: Path) -> None:
    source_dir = tmp_path / "mock_config"
    source_dir.mkdir()
    (source_dir / "kdeglobals").write_text("[General]\nfont=Inter\n")

    backup_dir = tmp_path / "snapshots"
    bm = BackupManager(backup_root=backup_dir, source_config_dir=source_dir)

    m1 = bm.create_snapshot("First")
    m2 = bm.create_snapshot("Second")
    m3 = bm.create_snapshot("Third")

    snaps = bm.list_snapshots()
    assert len(snaps) == 3
    # Check newest first
    assert snaps[0].id == m3.id
    assert snaps[1].id == m2.id
    assert snaps[2].id == m1.id

