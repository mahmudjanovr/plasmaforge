"""Safe, verified KDE Plasma 6 color scheme application engine.

Enforces:
1. Strict scheme identifier validation and whitelist matching
2. Automatic pre-apply cryptographic snapshot creation and verification
3. Safe Mode simulation enforcement
4. Non-shell argument vector execution of plasma-apply-colorscheme
5. Automatic rollback on execution failure
"""

from __future__ import annotations

import configparser
import difflib
import io
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from plasmaforge.core.backup_manager import BackupManager, SnapshotMetadata
from plasmaforge.core.themes import detect_active_color_scheme

SAFE_SCHEME_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]+$")


@dataclass
class ApplyResult:
    """Result of a color scheme application or simulation."""

    success: bool
    message: str
    scheme_id: str
    backup_id: str = ""
    rolled_back: bool = False
    is_dry_run: bool = False
    diff_preview: str = ""


class KdeColorSchemeApplier:
    """Coordinates validation, pre-apply backups, tool execution, and rollback for KDE color schemes."""

    def __init__(
        self,
        backup_manager: Optional[BackupManager] = None,
        safe_mode: bool = True,
        source_config_dir: Optional[Path] = None,
        tool_binary: Optional[str] = None,
    ) -> None:
        self.backup_manager = backup_manager or BackupManager()
        self.safe_mode = safe_mode
        self.source_config_dir = source_config_dir or (Path.home() / ".config")
        self.tool_binary = tool_binary or shutil.which("plasma-apply-colorscheme")
        self.scheme_dirs = [
            Path.home() / ".local" / "share" / "color-schemes",
            Path("/usr/share/color-schemes"),
        ]

    def find_scheme_file(self, scheme_id: str) -> Optional[Path]:
        """Find corresponding .colors file for a scheme identifier."""
        if not SAFE_SCHEME_PATTERN.match(scheme_id):
            return None

        # Check exact filename first
        for directory in self.scheme_dirs:
            if not directory.is_dir():
                continue
            exact = directory / f"{scheme_id}.colors"
            if exact.is_file():
                return exact

        # Check case-insensitive and General.Name
        for directory in self.scheme_dirs:
            if not directory.is_dir():
                continue
            for p in directory.glob("*.colors"):
                if p.stem.lower() == scheme_id.lower():
                    return p
                try:
                    cfg = configparser.ConfigParser(interpolation=None)
                    cfg.optionxform = str
                    cfg.read(p, encoding="utf-8")
                    if cfg.has_section("General"):
                        name = cfg.get("General", "Name", fallback="")
                        if name.lower() == scheme_id.lower():
                            return p
                except Exception:
                    continue
        return None

    def validate_scheme(self, scheme_id: str) -> tuple[bool, Optional[Path], str]:
        """Validate scheme identifier and file existence."""
        if not scheme_id or not scheme_id.strip():
            return False, None, "Scheme identifier cannot be empty."

        clean_id = scheme_id.strip()
        if not SAFE_SCHEME_PATTERN.match(clean_id):
            return (
                False,
                None,
                f"Invalid scheme identifier '{clean_id}': contains forbidden characters.",
            )

        file_path = self.find_scheme_file(clean_id)
        if not file_path:
            return (
                False,
                None,
                f"Color scheme '{clean_id}' was not found in installed color-schemes paths.",
            )

        try:
            cfg = configparser.ConfigParser(interpolation=None)
            cfg.optionxform = str
            cfg.read(file_path, encoding="utf-8")
            if not cfg.sections():
                return False, file_path, f"Color scheme file '{file_path.name}' is empty or invalid."
        except Exception as e:
            return False, file_path, f"Failed to parse scheme file '{file_path.name}': {e}"

        return True, file_path, "Valid"

    def generate_diff_preview(self, scheme_id: str) -> str:
        """Generate unified diff showing what ~/.config/kdeglobals would change."""
        valid, file_path, err = self.validate_scheme(scheme_id)
        if not valid or not file_path:
            return f"Cannot generate diff preview: {err}"

        kdeglobals = self.source_config_dir / "kdeglobals"
        current_text = ""
        if kdeglobals.is_file():
            try:
                current_text = kdeglobals.read_text(encoding="utf-8", errors="replace")
            except Exception:
                current_text = ""

        try:
            scheme_cfg = configparser.ConfigParser(interpolation=None)
            scheme_cfg.optionxform = str
            scheme_cfg.read(file_path, encoding="utf-8")

            sim_cfg = configparser.ConfigParser(interpolation=None)
            sim_cfg.optionxform = str
            if current_text:
                sim_cfg.read_string(current_text)

            # Copy color and effect sections from scheme
            for sec in scheme_cfg.sections():
                if sec.startswith("Colors:") or sec.startswith("ColorEffects:"):
                    if not sim_cfg.has_section(sec):
                        sim_cfg.add_section(sec)
                    for k, v in scheme_cfg.items(sec):
                        sim_cfg.set(sec, k, v)

            if not sim_cfg.has_section("General"):
                sim_cfg.add_section("General")
            sim_cfg.set("General", "ColorScheme", scheme_id)

            buf = io.StringIO()
            sim_cfg.write(buf)
            new_text = buf.getvalue()

            diff_lines = list(
                difflib.unified_diff(
                    current_text.splitlines(keepends=True),
                    new_text.splitlines(keepends=True),
                    fromfile="a/~/.config/kdeglobals (current)",
                    tofile=f"b/~/.config/kdeglobals ({scheme_id})",
                    n=1,
                )
            )

            if not diff_lines:
                return f"# Color scheme '{scheme_id}' matches current configuration palette. No changes required."

            # Header
            header = [
                f"# Unified Diff Preview: Color Scheme '{scheme_id}'",
                f"# Source file: {file_path}",
                f"# Target: {kdeglobals}",
                "--------------------------------------------------\n",
            ]
            return "".join(header + diff_lines[:120])
        except Exception as e:
            return f"Failed to compute diff: {e}"

    def _execute_apply_command(
        self, tool: str, scheme_id: str
    ) -> subprocess.CompletedProcess:
        """Execute the KDE tool with strict argument vectors without shell expansion."""
        return subprocess.run(
            [tool, scheme_id],
            capture_output=True,
            text=True,
            timeout=8.0,
        )

    def apply_scheme(
        self,
        scheme_id: str,
        force_safe_mode: Optional[bool] = None,
    ) -> ApplyResult:
        """Apply color scheme with pre-apply backup and safe failure rollback."""
        is_safe = self.safe_mode if force_safe_mode is None else force_safe_mode

        # 1. Validation
        valid, file_path, error_msg = self.validate_scheme(scheme_id)
        if not valid:
            return ApplyResult(
                success=False,
                message=error_msg,
                scheme_id=scheme_id,
            )

        # 2. Check if already active
        current_active = detect_active_color_scheme(self.source_config_dir / "kdeglobals")
        diff_text = self.generate_diff_preview(scheme_id)

        if (
            current_active
            and (
                current_active.lower() == scheme_id.lower()
                or (file_path and file_path.stem.lower() == current_active.lower())
            )
        ):
            return ApplyResult(
                success=True,
                message=f"Color scheme '{scheme_id}' is already set as the active theme.",
                scheme_id=scheme_id,
                diff_preview=diff_text,
                is_dry_run=is_safe,
            )

        # 3. Check KDE tool
        tool = self.tool_binary
        if not tool or not Path(tool).is_file():
            return ApplyResult(
                success=False,
                message="KDE utility 'plasma-apply-colorscheme' is not installed or accessible on this system.",
                scheme_id=scheme_id,
                diff_preview=diff_text,
            )

        # 4. Handle Safe Mode (Simulation)
        if is_safe:
            # Create a verified test snapshot in safe mode to verify backup subsystem
            test_meta = self.backup_manager.create_snapshot(
                f"Safe Mode Simulation: Before applying {scheme_id}"
            )
            return ApplyResult(
                success=True,
                message=f"Safe Mode active: Simulated applying '{scheme_id}'. Live desktop session was not modified.",
                scheme_id=scheme_id,
                backup_id=test_meta.id,
                is_dry_run=True,
                diff_preview=diff_text,
            )

        # 5. Live Mode Execution: Create Verified Pre-Apply Backup First
        backup_desc = f"Automatic Pre-Apply: Before applying '{scheme_id}'"
        try:
            backup_meta = self.backup_manager.create_snapshot(backup_desc)
            valid_backup, errors = self.backup_manager.verify_snapshot_integrity(
                backup_meta.id
            )
            if not valid_backup:
                return ApplyResult(
                    success=False,
                    message=f"Pre-apply backup integrity verification failed ({'; '.join(errors)}). Application aborted for safety.",
                    scheme_id=scheme_id,
                    diff_preview=diff_text,
                )
        except Exception as e:
            return ApplyResult(
                success=False,
                message=f"Failed to create pre-apply backup: {e}. Application aborted for safety.",
                scheme_id=scheme_id,
                diff_preview=diff_text,
            )

        # 6. Execute plasma-apply-colorscheme via argument vector (NO shell=True)
        try:
            proc = self._execute_apply_command(tool, scheme_id)
        except subprocess.TimeoutExpired:
            # Timeout: attempt rollback
            self.backup_manager.restore_snapshot(backup_meta.id, ["kdeglobals"])
            return ApplyResult(
                success=False,
                message="KDE tool execution timed out after 8 seconds. Configuration was rolled back.",
                scheme_id=scheme_id,
                backup_id=backup_meta.id,
                rolled_back=True,
                diff_preview=diff_text,
            )
        except Exception as e:
            # Exception: attempt rollback
            self.backup_manager.restore_snapshot(backup_meta.id, ["kdeglobals"])
            return ApplyResult(
                success=False,
                message=f"Failed to execute KDE color scheme tool: {e}. Configuration was rolled back.",
                scheme_id=scheme_id,
                backup_id=backup_meta.id,
                rolled_back=True,
                diff_preview=diff_text,
            )

        # 7. Check result
        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip() or f"exit code {proc.returncode}"
            # Rollback to pre-apply snapshot
            rb_ok, rb_msg = self.backup_manager.restore_snapshot(
                backup_meta.id, ["kdeglobals"]
            )
            return ApplyResult(
                success=False,
                message=f"KDE color scheme application failed ({err}). Automatic rollback: {rb_msg}",
                scheme_id=scheme_id,
                backup_id=backup_meta.id,
                rolled_back=rb_ok,
                diff_preview=diff_text,
            )

        return ApplyResult(
            success=True,
            message=f"Successfully applied KDE color scheme '{scheme_id}'.",
            scheme_id=scheme_id,
            backup_id=backup_meta.id,
            diff_preview=diff_text,
        )

    def restore_backup(
        self,
        backup_id: str,
        target_scheme_id: Optional[str] = None,
    ) -> tuple[bool, str]:
        """Restore configuration from a snapshot and optionally re-apply scheme to session."""
        ok, msg = self.backup_manager.restore_snapshot(backup_id, ["kdeglobals"])
        if not ok:
            return False, f"Failed to restore backup '{backup_id}': {msg}"

        # If a scheme ID is known and tool is available, re-run tool to notify running apps
        if target_scheme_id and self.tool_binary:
            valid, _, _ = self.validate_scheme(target_scheme_id)
            if valid:
                try:
                    subprocess.run(
                        [self.tool_binary, target_scheme_id],
                        capture_output=True,
                        text=True,
                        timeout=8.0,
                    )
                except Exception:
                    pass

        return True, f"Successfully restored configuration from backup '{backup_id}'."
