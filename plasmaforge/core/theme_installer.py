"""Safe download, validation, extraction, and installation engine for KDE Global Themes.

Guarantees:
1. Strict archive path traversal protection (rejects absolute paths, '..', and escaping symlinks).
2. Archive checksum verification against provider manifest when available.
3. Package structure and metadata validation (metadata.json / metadata.desktop, contents/defaults).
4. Safe installation exclusively into per-user directory (~/.local/share/plasma/look-and-feel).
5. Cancellation and download progress reporting.
6. Safe cleanup of temporary staging files.
"""

from __future__ import annotations

import configparser
import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


SAFE_PACKAGE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_.\-]+$")
DEFAULT_USER_AGENT = "PlasmaForge/1.0 (KDE Global Theme Installer; Linux)"


class ThemeInstallationError(RuntimeError):
    """Raised when theme validation or installation fails."""


class ThemeSecurityViolationError(ThemeInstallationError):
    """Raised when an archive contains path traversal or invalid targets."""


@dataclass
class InstalledThemeInfo:
    """Metadata for an installed KDE Look and Feel (Global Theme) package."""

    id: str
    name: str
    path: str
    version: str
    author: str
    description: str
    is_user_installed: bool
    components: Dict[str, str] = field(default_factory=dict)
    has_defaults: bool = False
    is_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ThemePackageInspector:
    """Discovers and inspects installed KDE Look and Feel packages."""

    def __init__(self, user_dir: Optional[Path] = None, system_dirs: Optional[List[Path]] = None) -> None:
        xdg_data_home = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
        self.user_dir = user_dir or (xdg_data_home / "plasma" / "look-and-feel")

        xdg_data_dirs_raw = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
        xdg_dirs = [Path(p) for p in xdg_data_dirs_raw.split(":") if p.strip()]

        s_dirs: List[Path] = system_dirs or []
        if not s_dirs:
            for d in xdg_dirs:
                sd = d / "plasma" / "look-and-feel"
                if sd not in s_dirs:
                    s_dirs.append(sd)
            fallback_usr = Path("/usr/share/plasma/look-and-feel")
            if fallback_usr not in s_dirs:
                s_dirs.append(fallback_usr)
        self.system_dirs = s_dirs

    def get_search_directories(self) -> List[Tuple[Path, bool]]:
        """Return search directories as tuples of (Path, is_user)."""
        dirs: List[Tuple[Path, bool]] = []
        if self.user_dir:
            dirs.append((self.user_dir, True))
        for sd in self.system_dirs:
            dirs.append((sd, False))
        return dirs

    def list_installed_themes(self, active_id: str = "") -> List[InstalledThemeInfo]:
        """Discover all valid installed Look and Feel packages across user and system directories."""
        installed: List[InstalledThemeInfo] = []
        seen_ids: Set[str] = set()

        for search_dir, is_user in self.get_search_directories():
            if not search_dir.is_dir():
                continue

            for sub in sorted(search_dir.iterdir()):
                if not sub.is_dir() or sub.name.startswith("."):
                    continue

                theme_id = sub.name
                if theme_id in seen_ids:
                    continue

                meta = self.inspect_package_directory(sub, is_user=is_user)
                if meta:
                    meta.is_active = bool(
                        active_id and (active_id.lower() == theme_id.lower() or active_id.lower() == meta.name.lower())
                    )
                    installed.append(meta)
                    seen_ids.add(theme_id)

        return installed

    def inspect_package_directory(self, pkg_dir: Path, is_user: bool = False) -> Optional[InstalledThemeInfo]:
        """Inspect a single Look and Feel package directory and parse its metadata and defaults."""
        if not pkg_dir.is_dir():
            return None

        theme_id = pkg_dir.name
        name = theme_id
        version = "1.0"
        author = "KDE Community"
        description = "Global Theme package"

        # Check metadata.json first (modern Plasma 6 standard)
        meta_json = pkg_dir / "metadata.json"
        if meta_json.is_file():
            try:
                with open(meta_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    kplugin = data.get("KPlugin", {})
                    name = kplugin.get("Name", name)
                    version = str(kplugin.get("Version", version))
                    description = kplugin.get("Description", description)
                    theme_id = kplugin.get("Id", theme_id)
                    authors = kplugin.get("Authors", [])
                    if authors and isinstance(authors, list):
                        first = authors[0]
                        if isinstance(first, dict):
                            author = first.get("Name", author)
                        elif isinstance(first, str):
                            author = first
            except Exception:
                pass
        else:
            # Check metadata.desktop fallback (Plasma 5 legacy packages)
            meta_desk = pkg_dir / "metadata.desktop"
            if meta_desk.is_file():
                try:
                    cfg = configparser.ConfigParser(interpolation=None)
                    cfg.optionxform = str
                    cfg.read(meta_desk, encoding="utf-8")
                    sec = "Desktop Entry" if cfg.has_section("Desktop Entry") else cfg.sections()[0]
                    name = cfg.get(sec, "Name", fallback=name)
                    description = cfg.get(sec, "Comment", fallback=description)
                    author = cfg.get(sec, "X-KDE-PluginInfo-Author", fallback=author)
                    version = cfg.get(sec, "X-KDE-PluginInfo-Version", fallback=version)
                    theme_id = cfg.get(sec, "X-KDE-PluginInfo-Name", fallback=theme_id)
                except Exception:
                    pass

        # Parse contents/defaults to discover affected components
        components: Dict[str, str] = {}
        defaults_file = pkg_dir / "contents" / "defaults"
        has_defaults = defaults_file.is_file()
        if has_defaults:
            try:
                cfg = configparser.ConfigParser(interpolation=None)
                cfg.optionxform = str
                cfg.read(defaults_file, encoding="utf-8")

                for sec in cfg.sections():
                    for k, v in cfg.items(sec):
                        key_desc = f"[{sec}] {k}"
                        components[key_desc] = v

                        # Map to friendly component names
                        if "kdeglobals" in sec and k == "ColorScheme":
                            components["Color Scheme"] = v
                        elif "kdeglobals" in sec and k == "widgetStyle":
                            components["Widget Style"] = v
                        elif "kdeglobals" in sec and k == "Theme" and "Icons" in sec:
                            components["Icon Theme"] = v
                        elif "plasmarc" in sec and k == "name" and "Theme" in sec:
                            components["Plasma Desktop Theme"] = v
                        elif "kcminputrc" in sec and k == "cursorTheme":
                            components["Cursor Theme"] = v
                        elif "Wallpaper" in sec and k == "Image":
                            components["Wallpaper"] = v
                        elif "kwinrc" in sec and "kdecoration2" in sec and k == "theme":
                            components["Window Decoration"] = v
                        elif "kwinrc" in sec and "WindowSwitcher" in sec:
                            components["Window Switcher"] = v
            except Exception:
                pass

        return InstalledThemeInfo(
            id=theme_id,
            name=name,
            path=str(pkg_dir),
            version=version,
            author=author,
            description=description,
            is_user_installed=is_user,
            components=components,
            has_defaults=has_defaults,
        )


class ThemeDownloader:
    """Manages resilient download with progress reporting, timeout handling, and cancellation."""

    def __init__(self, timeout: float = 20.0, user_agent: str = DEFAULT_USER_AGENT) -> None:
        self.timeout = timeout
        self.user_agent = user_agent
        self._cancelled = False

    def cancel(self) -> None:
        """Signal ongoing download to cancel immediately."""
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def download_to_file(
        self,
        url: str,
        target_path: Path,
        expected_md5: str = "",
        progress_callback: Optional[Callable[[int, int, float, str], None]] = None,
    ) -> bool:
        """Download URL stream to target_path with chunked hashing and progress updates."""
        self._cancelled = False
        target_path.parent.mkdir(parents=True, exist_ok=True)

        req = urllib.request.Request(
            url,
            headers={"User-Agent": self.user_agent},
        )

        md5_hasher = hashlib.md5() if expected_md5 else None
        bytes_received = 0
        total_bytes = 0

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status_code = resp.getcode()
                if status_code != 200:
                    raise ThemeInstallationError(f"Download failed with HTTP status {status_code}")

                content_len = resp.headers.get("Content-Length")
                if content_len:
                    try:
                        total_bytes = int(content_len)
                    except ValueError:
                        total_bytes = 0

                with open(target_path, "wb") as out_file:
                    chunk_size = 32768  # 32 KB chunks
                    while True:
                        if self._cancelled:
                            # Clean up partial download
                            out_file.close()
                            if target_path.exists():
                                target_path.unlink()
                            raise ThemeInstallationError("Download cancelled by user.")

                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break

                        out_file.write(chunk)
                        bytes_received += len(chunk)
                        if md5_hasher:
                            md5_hasher.update(chunk)

                        if progress_callback:
                            percent = (bytes_received / total_bytes * 100.0) if total_bytes > 0 else 0.0
                            progress_callback(
                                bytes_received,
                                total_bytes,
                                percent,
                                f"Downloading: {bytes_received // 1024} KB" + (f" / {total_bytes // 1024} KB" if total_bytes > 0 else ""),
                            )
        except urllib.error.URLError as e:
            if target_path.exists():
                target_path.unlink()
            raise ThemeInstallationError(f"Network error during download: {e.reason}") from e
        except Exception as e:
            if target_path.exists():
                target_path.unlink()
            raise ThemeInstallationError(f"Failed to complete download: {e}") from e

        # Check MD5 if provided
        if expected_md5 and md5_hasher:
            actual_md5 = md5_hasher.hexdigest().lower()
            if actual_md5 != expected_md5.lower().strip():
                if target_path.exists():
                    target_path.unlink()
                raise ThemeInstallationError(
                    f"Integrity check failed: MD5 mismatch (expected {expected_md5}, got {actual_md5})"
                )

        return True


class ThemeInstaller:
    """Safe validator and installer for KDE Global Theme packages."""

    def __init__(
        self,
        user_install_dir: Optional[Path] = None,
        downloader: Optional[ThemeDownloader] = None,
        inspector: Optional[ThemePackageInspector] = None,
    ) -> None:
        xdg_data_home = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
        self.user_install_dir = user_install_dir or (xdg_data_home / "plasma" / "look-and-feel")
        self.downloader = downloader or ThemeDownloader()
        self.inspector = inspector or ThemePackageInspector(user_dir=self.user_install_dir)

    def validate_archive_member(self, member_name: str, dest_dir: Path) -> None:
        """Ensure an archive member path is strictly safe against path traversal."""
        if not member_name or not member_name.strip():
            raise ThemeSecurityViolationError("Empty archive entry name encountered.")

        # Reject absolute paths
        if member_name.startswith("/") or member_name.startswith("\\"):
            raise ThemeSecurityViolationError(
                f"Path traversal detected: absolute path '{member_name}' is forbidden."
            )

        # Reject '..' components
        parts = Path(member_name).parts
        if any(p == ".." for p in parts):
            raise ThemeSecurityViolationError(
                f"Path traversal detected: entry '{member_name}' contains parent directory '..'."
            )

        # Check resolved target path stays within dest_dir
        dest_resolved = dest_dir.resolve()
        target_resolved = (dest_dir / member_name).resolve()
        try:
            target_resolved.relative_to(dest_resolved)
        except ValueError:
            raise ThemeSecurityViolationError(
                f"Path traversal detected: entry '{member_name}' resolves outside extraction root."
            )

    def safe_extract_archive(self, archive_path: Path, extraction_root: Path) -> Path:
        """Extract tar or zip archive safely, rejecting malicious paths."""
        extraction_root.mkdir(parents=True, exist_ok=True)

        if tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path, "r:*") as tar:
                for member in tar.getmembers():
                    self.validate_archive_member(member.name, extraction_root)
                    if member.issym() or member.islnk():
                        # Validate link target does not point to sensitive absolute paths
                        link_target = member.linkname
                        if link_target.startswith("/") or ".." in link_target:
                            # Verify resolved symlink target remains inside extraction root
                            resolved_link = (extraction_root / member.name).parent / link_target
                            try:
                                resolved_link.resolve().relative_to(extraction_root.resolve())
                            except ValueError:
                                raise ThemeSecurityViolationError(
                                    f"Forbidden symlink '{member.name}' -> '{link_target}' escapes extraction root."
                                )
                tar.extractall(path=extraction_root)
        elif zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, "r") as zf:
                for name in zf.namelist():
                    self.validate_archive_member(name, extraction_root)
                zf.extractall(path=extraction_root)
        else:
            raise ThemeInstallationError(f"Unsupported or corrupted archive format: '{archive_path.name}'.")

        return extraction_root

    def locate_package_root(self, extraction_root: Path) -> Path:
        """Find the root directory of the Look and Feel package within extracted files."""
        # Check root itself
        if (extraction_root / "metadata.json").is_file() or (extraction_root / "metadata.desktop").is_file():
            return extraction_root

        # Check immediate subdirectories
        subdirs = [p for p in extraction_root.iterdir() if p.is_dir() and not p.name.startswith(".")]
        for s in subdirs:
            if (s / "metadata.json").is_file() or (s / "metadata.desktop").is_file():
                return s

        # Recursive search for metadata.json up to 2 levels deep
        for s in subdirs:
            for nested in s.iterdir():
                if nested.is_dir() and ((nested / "metadata.json").is_file() or (nested / "metadata.desktop").is_file()):
                    return nested

        raise ThemeInstallationError(
            "Extracted archive does not contain valid Global Theme metadata (metadata.json or metadata.desktop)."
        )

    def validate_package_metadata(self, pkg_dir: Path) -> Tuple[str, str]:
        """Validate package structure and return (package_id, theme_name)."""
        meta_json = pkg_dir / "metadata.json"
        meta_desktop = pkg_dir / "metadata.desktop"

        package_id = ""
        theme_name = ""

        if meta_json.is_file():
            try:
                with open(meta_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    structure = data.get("KPackageStructure", "")
                    kplugin = data.get("KPlugin", {})
                    package_id = kplugin.get("Id", "") or pkg_dir.name
                    theme_name = kplugin.get("Name", "") or package_id

                    # If KPackageStructure is specified, verify compatibility
                    if structure and structure != "Plasma/LookAndFeel":
                        # Some themes omit structure or set to Plasma/Generic, allow if contents exists
                        if not (pkg_dir / "contents").is_dir():
                            raise ThemeInstallationError(
                                f"Incompatible package structure: '{structure}', expected 'Plasma/LookAndFeel'."
                            )
            except json.JSONDecodeError as e:
                raise ThemeInstallationError(f"Malformed metadata.json in package: {e}")
        elif meta_desktop.is_file():
            try:
                cfg = configparser.ConfigParser(interpolation=None)
                cfg.optionxform = str
                cfg.read(meta_desktop, encoding="utf-8")
                sec = "Desktop Entry" if cfg.has_section("Desktop Entry") else cfg.sections()[0]
                package_id = cfg.get(sec, "X-KDE-PluginInfo-Name", fallback=pkg_dir.name)
                theme_name = cfg.get(sec, "Name", fallback=package_id)
            except Exception as e:
                raise ThemeInstallationError(f"Malformed metadata.desktop in package: {e}")
        else:
            raise ThemeInstallationError("Package is missing metadata.json or metadata.desktop.")

        package_id = package_id.strip()
        if not package_id or not SAFE_PACKAGE_ID_PATTERN.match(package_id):
            # Fall back to sanitized directory name
            sanitized = re.sub(r"[^a-zA-Z0-9_.\-]", "_", pkg_dir.name).strip()
            if sanitized and SAFE_PACKAGE_ID_PATTERN.match(sanitized):
                package_id = sanitized
            else:
                raise ThemeInstallationError(f"Invalid package identifier '{package_id}'.")

        return package_id, theme_name or package_id

    def install_from_archive(
        self,
        archive_path: Path,
        expected_id: str = "",
        force_overwrite: bool = True,
    ) -> Tuple[bool, str, Optional[InstalledThemeInfo]]:
        """Validate archive and install Look and Feel package into user directory."""
        with tempfile.TemporaryDirectory(prefix="plasmaforge_extract_") as extract_temp:
            ext_path = Path(extract_temp)
            try:
                self.safe_extract_archive(archive_path, ext_path)
            except ThemeSecurityViolationError as e:
                return False, f"Security check failed: {e}", None
            except Exception as e:
                return False, f"Failed to extract theme package: {e}", None

            try:
                pkg_dir = self.locate_package_root(ext_path)
                pkg_id, theme_name = self.validate_package_metadata(pkg_dir)
            except ThemeInstallationError as e:
                return False, f"Package validation error: {e}", None

            target_id = pkg_id or expected_id
            if not target_id or not SAFE_PACKAGE_ID_PATTERN.match(target_id):
                return False, f"Unacceptable theme package ID: '{target_id}'", None

            target_dir = self.user_install_dir / target_id

            # Safe atomic copy to destination
            try:
                self.user_install_dir.mkdir(parents=True, exist_ok=True)
                if target_dir.exists():
                    if not force_overwrite:
                        return False, f"Theme '{target_id}' is already installed.", None
                    # Clean previous installation of this specific package
                    shutil.rmtree(target_dir)

                shutil.copytree(pkg_dir, target_dir)
            except Exception as e:
                return False, f"Filesystem error installing theme to '{target_dir}': {e}", None

            # Verify installed package
            meta = self.inspector.inspect_package_directory(target_dir, is_user=True)
            if not meta:
                return False, f"Installed package verification failed at '{target_dir}'.", None

            return True, f"Successfully installed Global Theme '{meta.name}' ({meta.id}).", meta

    def download_and_install(
        self,
        download_url: str,
        expected_md5: str = "",
        theme_id: str = "",
        progress_callback: Optional[Callable[[int, int, float, str], None]] = None,
    ) -> Tuple[bool, str, Optional[InstalledThemeInfo]]:
        """Full safe workflow: download, verify hash, validate archive, and install."""
        with tempfile.TemporaryDirectory(prefix="plasmaforge_dl_") as dl_temp:
            archive_file = Path(dl_temp) / "package_download.archive"
            try:
                if progress_callback:
                    progress_callback(0, 0, 0.0, "Starting download...")
                self.downloader.download_to_file(
                    url=download_url,
                    target_path=archive_file,
                    expected_md5=expected_md5,
                    progress_callback=progress_callback,
                )
            except ThemeInstallationError as e:
                return False, f"Download failed: {e}", None
            except Exception as e:
                return False, f"Unexpected download failure: {e}", None

            if progress_callback:
                progress_callback(100, 100, 100.0, "Validating and extracting package...")

            return self.install_from_archive(archive_file, expected_id=theme_id)

    def uninstall_theme(self, theme_id: str) -> Tuple[bool, str]:
        """Safely remove a user-installed Look and Feel theme package."""
        if not theme_id or not SAFE_PACKAGE_ID_PATTERN.match(theme_id):
            return False, f"Invalid theme identifier: '{theme_id}'"

        target_dir = self.user_install_dir / theme_id
        if not target_dir.exists():
            return False, f"Theme '{theme_id}' is not installed in user look-and-feel directory."

        # Guard against path traversal
        try:
            target_dir.resolve().relative_to(self.user_install_dir.resolve())
        except ValueError:
            return False, f"Security violation: theme path escapes '{self.user_install_dir}'."

        if not target_dir.is_dir():
            return False, f"Theme path '{target_dir}' is not a directory."

        try:
            shutil.rmtree(target_dir)
            return True, f"Successfully uninstalled theme '{theme_id}'."
        except Exception as e:
            return False, f"Failed to uninstall theme '{theme_id}': {e}"
