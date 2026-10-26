"""Unit tests for safe Global Theme package validation, extraction, path traversal protection, and per-user installation."""

import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import zipfile
import pytest

from plasmaforge.core.theme_installer import (
    InstalledThemeInfo,
    ThemeDownloader,
    ThemeInstallationError,
    ThemeInstaller,
    ThemePackageInspector,
    ThemeSecurityViolationError,
)


def _create_valid_theme_tar(archive_path: Path, pkg_id: str = "org.test.theme", name: str = "Test Theme") -> Path:
    """Helper to build a valid Look and Feel package tar.gz in memory/disk."""
    meta = {
        "KPackageStructure": "Plasma/LookAndFeel",
        "KPlugin": {
            "Id": pkg_id,
            "Name": name,
            "Version": "1.2",
            "Description": "A test global theme",
            "Authors": [{"Name": "Tester"}],
        },
    }
    defaults = """[kdeglobals][General]
ColorScheme=BreezeDark

[plasmarc][Theme]
name=breeze-dark

[kcminputrc][Mouse]
cursorTheme=breeze_cursors
"""
    with tarfile.open(archive_path, "w:gz") as tar:
        # Add folder
        ti_dir = tarfile.TarInfo(f"{pkg_id}/")
        ti_dir.type = tarfile.DIRTYPE
        tar.addfile(ti_dir)

        # Add metadata.json
        meta_bytes = json.dumps(meta).encode("utf-8")
        ti_meta = tarfile.TarInfo(f"{pkg_id}/metadata.json")
        ti_meta.size = len(meta_bytes)
        tar.addfile(ti_meta, io.BytesIO(meta_bytes))

        # Add contents/
        ti_contents = tarfile.TarInfo(f"{pkg_id}/contents/")
        ti_contents.type = tarfile.DIRTYPE
        tar.addfile(ti_contents)

        # Add contents/defaults
        def_bytes = defaults.encode("utf-8")
        ti_def = tarfile.TarInfo(f"{pkg_id}/contents/defaults")
        ti_def.size = len(def_bytes)
        tar.addfile(ti_def, io.BytesIO(def_bytes))

    return archive_path


def test_safe_extraction_valid_archive(tmp_path: Path) -> None:
    """Verify clean extraction of a well-formed Look and Feel package."""
    archive = tmp_path / "valid.tar.gz"
    _create_valid_theme_tar(archive, pkg_id="org.sample.theme", name="Sample Theme")

    extract_dest = tmp_path / "extracted"
    installer = ThemeInstaller(user_install_dir=tmp_path / "installed")
    installer.safe_extract_archive(archive, extract_dest)

    assert (extract_dest / "org.sample.theme" / "metadata.json").is_file()
    assert (extract_dest / "org.sample.theme" / "contents" / "defaults").is_file()


def test_path_traversal_absolute_path_rejected(tmp_path: Path) -> None:
    """Verify archive containing absolute paths is rejected immediately."""
    malicious_tar = tmp_path / "malicious_abs.tar.gz"
    with tarfile.open(malicious_tar, "w:gz") as tar:
        ti = tarfile.TarInfo("/etc/malicious.conf")
        ti.size = 5
        tar.addfile(ti, io.BytesIO(b"owned"))

    extract_dest = tmp_path / "extracted"
    installer = ThemeInstaller(user_install_dir=tmp_path / "installed")

    with pytest.raises(ThemeSecurityViolationError) as exc_info:
        installer.safe_extract_archive(malicious_tar, extract_dest)
    assert "absolute path" in str(exc_info.value).lower()


def test_path_traversal_parent_dir_rejected(tmp_path: Path) -> None:
    """Verify archive with '../' parent directory references is strictly rejected."""
    malicious_tar = tmp_path / "malicious_parent.tar.gz"
    with tarfile.open(malicious_tar, "w:gz") as tar:
        ti = tarfile.TarInfo("org.test.theme/../../outside.txt")
        ti.size = 5
        tar.addfile(ti, io.BytesIO(b"owned"))

    extract_dest = tmp_path / "extracted"
    installer = ThemeInstaller(user_install_dir=tmp_path / "installed")

    with pytest.raises(ThemeSecurityViolationError) as exc_info:
        installer.safe_extract_archive(malicious_tar, extract_dest)
    assert "parent directory" in str(exc_info.value).lower()


def test_path_traversal_zip_slip_rejected(tmp_path: Path) -> None:
    """Verify zip archive with path traversal is rejected."""
    malicious_zip = tmp_path / "malicious.zip"
    with zipfile.ZipFile(malicious_zip, "w") as zf:
        zf.writestr("../../etc/shadow_fake", "root:x:0:0")

    extract_dest = tmp_path / "extracted"
    installer = ThemeInstaller(user_install_dir=tmp_path / "installed")

    with pytest.raises(ThemeSecurityViolationError) as exc_info:
        installer.safe_extract_archive(malicious_zip, extract_dest)
    assert "parent directory" in str(exc_info.value).lower()


def test_corrupted_archive_rejected(tmp_path: Path) -> None:
    """Verify corrupted non-archive payload is rejected with clean error."""
    corrupt_file = tmp_path / "corrupt.tar.gz"
    corrupt_file.write_bytes(b"This is definitely not a tar or zip file!")

    extract_dest = tmp_path / "extracted"
    installer = ThemeInstaller(user_install_dir=tmp_path / "installed")

    with pytest.raises(ThemeInstallationError) as exc_info:
        installer.safe_extract_archive(corrupt_file, extract_dest)
    assert "corrupted archive" in str(exc_info.value).lower()


def test_missing_metadata_rejected(tmp_path: Path) -> None:
    """Verify archive with no metadata.json or metadata.desktop is rejected."""
    empty_tar = tmp_path / "empty_theme.tar.gz"
    with tarfile.open(empty_tar, "w:gz") as tar:
        ti = tarfile.TarInfo("random_folder/somefile.txt")
        ti.size = 4
        tar.addfile(ti, io.BytesIO(b"data"))

    installer = ThemeInstaller(user_install_dir=tmp_path / "installed")
    ok, msg, info = installer.install_from_archive(empty_tar)
    assert ok is False
    assert "metadata" in msg.lower()
    assert info is None


def test_safe_per_user_installation(tmp_path: Path) -> None:
    """Verify full installation into isolated user directory without touching unrelated files."""
    user_install_dir = tmp_path / "user_look_and_feel"
    unrelated_file = user_install_dir / "unrelated_user_file.txt"
    user_install_dir.mkdir(parents=True)
    unrelated_file.write_text("Do not touch me!")

    archive = tmp_path / "valid_theme.tar.gz"
    _create_valid_theme_tar(archive, pkg_id="org.plasmaforge.test", name="PlasmaForge Test")

    installer = ThemeInstaller(user_install_dir=user_install_dir)
    ok, msg, info = installer.install_from_archive(archive)

    assert ok is True
    assert info is not None
    assert info.id == "org.plasmaforge.test"
    assert info.name == "PlasmaForge Test"
    assert info.is_user_installed is True
    assert (user_install_dir / "org.plasmaforge.test" / "metadata.json").is_file()

    # Verify unrelated file was preserved untouched
    assert unrelated_file.is_file()
    assert unrelated_file.read_text() == "Do not touch me!"

    # Verify component extraction from contents/defaults
    assert info.components.get("Color Scheme") == "BreezeDark"
    assert info.components.get("Plasma Desktop Theme") == "breeze-dark"
    assert info.components.get("Cursor Theme") == "breeze_cursors"


def test_inspector_detects_installed_themes(tmp_path: Path) -> None:
    """Verify ThemePackageInspector lists installed themes across user and system paths."""
    user_dir = tmp_path / "user_laf"
    system_dir = tmp_path / "sys_laf"

    # Create one user theme
    u_pkg = user_dir / "org.user.theme"
    u_pkg.mkdir(parents=True)
    (u_pkg / "metadata.json").write_text(json.dumps({
        "KPlugin": {"Id": "org.user.theme", "Name": "User Theme", "Version": "1.0"}
    }))

    # Create one system theme
    s_pkg = system_dir / "org.system.theme"
    s_pkg.mkdir(parents=True)
    (s_pkg / "metadata.json").write_text(json.dumps({
        "KPlugin": {"Id": "org.system.theme", "Name": "System Theme", "Version": "2.0"}
    }))

    inspector = ThemePackageInspector(user_dir=user_dir, system_dirs=[system_dir])
    themes = inspector.list_installed_themes(active_id="org.user.theme")

    assert len(themes) == 2
    u_info = next(t for t in themes if t.id == "org.user.theme")
    s_info = next(t for t in themes if t.id == "org.system.theme")

    assert u_info.is_user_installed is True
    assert u_info.is_active is True
    assert s_info.is_user_installed is False
    assert s_info.is_active is False


def test_uninstall_theme(tmp_path: Path) -> None:
    """Verify safe removal of installed user theme and protection against path traversal."""
    user_install_dir = tmp_path / "user_laf"
    target_theme = user_install_dir / "org.removable.theme"
    target_theme.mkdir(parents=True)
    (target_theme / "metadata.json").write_text("{}")

    installer = ThemeInstaller(user_install_dir=user_install_dir)
    assert target_theme.exists()

    ok, msg = installer.uninstall_theme("org.removable.theme")
    assert ok is True
    assert not target_theme.exists()

    # Attempt path traversal uninstall
    ok_traversal, msg_traversal = installer.uninstall_theme("../unrelated")
    assert ok_traversal is False
    assert "invalid" in msg_traversal.lower() or "traversal" in msg_traversal.lower()


def test_download_md5_verification_failure(tmp_path: Path) -> None:
    """Verify download checksum verification failure cleans up temporary storage."""
    dl_file = tmp_path / "download.tar.gz"
    dl_file.write_bytes(b"content")

    downloader = ThemeDownloader()
    from unittest.mock import MagicMock, patch

    mock_resp = MagicMock()
    mock_resp.getcode.return_value = 200
    mock_resp.headers = {"Content-Length": "7"}
    mock_resp.read.side_effect = [b"content", b""]

    with patch("urllib.request.urlopen") as mock_url:
        mock_url.return_value.__enter__.return_value = mock_resp
        with pytest.raises(ThemeInstallationError) as exc_info:
            downloader.download_to_file(
                url="https://fake.url/theme.tar.gz",
                target_path=dl_file,
                expected_md5="00000000000000000000000000000000",
            )
        assert "MD5 mismatch" in str(exc_info.value)
        assert not dl_file.exists()


def test_download_cancellation(tmp_path: Path) -> None:
    """Verify download cancellation cleans up partial file."""
    dl_file = tmp_path / "download_cancel.tar.gz"
    downloader = ThemeDownloader()

    from unittest.mock import MagicMock, patch

    mock_resp = MagicMock()
    mock_resp.getcode.return_value = 200
    mock_resp.headers = {"Content-Length": "1000"}

    def side_effect_read(size):
        downloader.cancel()
        return b"partial_data"

    mock_resp.read.side_effect = side_effect_read

    with patch("urllib.request.urlopen") as mock_url:
        mock_url.return_value.__enter__.return_value = mock_resp
        with pytest.raises(ThemeInstallationError) as exc_info:
            downloader.download_to_file(
                url="https://fake.url/theme.tar.gz",
                target_path=dl_file,
            )
        assert "cancelled" in str(exc_info.value).lower()
        assert not dl_file.exists()
