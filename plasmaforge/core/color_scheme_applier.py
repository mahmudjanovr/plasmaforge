"""Safe, verified KDE Plasma 6 color scheme application engine.

Refactored in Phase 3 to use the unified TransactionalSafetyEngine:
1. Strict scheme identifier validation and whitelist matching
2. Automatic pre-apply cryptographic snapshot creation and verification
3. Safe Mode simulation enforcement
4. Non-shell argument vector execution of plasma-apply-colorscheme
5. Post-apply verification of ~/.config/kdeglobals
6. Automatic rollback on execution failure or verification failure
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

from plasmaforge.core.backup_manager import BackupManager
from plasmaforge.core.themes import detect_active_color_scheme
from plasmaforge.core.transaction import (
    ApplyOperation,
    TransactionalSafetyEngine,
    TransactionResult,
    TransactionState,
)

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
        import os

        xdg_data_home = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
        xdg_data_dirs_raw = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
        xdg_data_dirs = [Path(p) for p in xdg_data_dirs_raw.split(":") if p.strip()]

        dirs: List[Path] = [xdg_data_home / "color-schemes"]
        for d in xdg_data_dirs:
            sd = d / "color-schemes"
            if sd not in dirs:
                dirs.append(sd)
        fallback_usr = Path("/usr/share/color-schemes")
        if fallback_usr not in dirs:
            dirs.append(fallback_usr)
        self.scheme_dirs = dirs
        self.safety_engine = TransactionalSafetyEngine(
            backup_manager=self.backup_manager,
            safe_mode=self.safe_mode,
            source_config_dir=self.source_config_dir,
        )

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
        """Apply color scheme using the shared transactional safety workflow."""
        is_safe = self.safe_mode if force_safe_mode is None else force_safe_mode

        # 1. Validation of scheme definition
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

        # 3. Check KDE tool existence
        tool = self.tool_binary
        if not tool or not Path(tool).is_file():
            return ApplyResult(
                success=False,
                message="KDE utility 'plasma-apply-colorscheme' is not installed or accessible on this system.",
                scheme_id=scheme_id,
                diff_preview=diff_text,
            )

        # Collect allowed names for post-apply verification
        allowed_matches = {scheme_id.strip().lower()}
        if file_path:
            allowed_matches.add(file_path.stem.strip().lower())
            try:
                scfg = configparser.ConfigParser(interpolation=None)
                scfg.optionxform = str
                scfg.read(file_path, encoding="utf-8")
                if scfg.has_section("General"):
                    name_val = scfg.get("General", "Name", fallback="").strip()
                    if name_val:
                        allowed_matches.add(name_val.lower())
            except Exception:
                pass

        # 4. Construct ApplyOperation for TransactionalSafetyEngine
        def apply_step() -> tuple[bool, str]:
            try:
                proc = self._execute_apply_command(tool, scheme_id)
            except subprocess.TimeoutExpired:
                return False, "KDE tool execution timed out after 8 seconds."
            except Exception as e:
                return False, f"Failed to execute KDE color scheme tool: {e}"

            if proc.returncode != 0:
                err = proc.stderr.strip() or proc.stdout.strip() or f"exit code {proc.returncode}"
                return False, f"KDE color scheme application failed ({err})"

            return True, "Executed"

        def verify_step() -> tuple[bool, str]:
            # Post-apply verification: ensure kdeglobals exists and General.ColorScheme matches
            kdeglobals = self.source_config_dir / "kdeglobals"
            if not kdeglobals.is_file():
                return False, "Configuration file kdeglobals missing after apply."
            try:
                cfg = configparser.ConfigParser(interpolation=None)
                cfg.optionxform = str
                cfg.read(kdeglobals, encoding="utf-8")
                if cfg.has_option("General", "ColorScheme"):
                    val = cfg.get("General", "ColorScheme", fallback="").strip()
                    if val.lower() in allowed_matches:
                        return True, f"Verified: kdeglobals ColorScheme is '{val}'"
                    return (
                        False,
                        f"Verification failed: kdeglobals ColorScheme is '{val}', expected '{scheme_id}'."
                    )
                return False, "Verification failed: General.ColorScheme option missing in kdeglobals."
            except Exception as e:
                return False, f"Verification failed to parse kdeglobals: {e}"

        operation = ApplyOperation(
            id=f"apply_colorscheme_{scheme_id}",
            title=f"Apply KDE Color Scheme '{scheme_id}'",
            description=f"Applies color scheme '{scheme_id}' using plasma-apply-colorscheme",
            affected_files=["kdeglobals"],
            diff_preview=diff_text,
            validate_fn=lambda: (True, "Valid"),
            apply_fn=apply_step,
            verify_fn=verify_step,
        )

        # 5. Execute transactionally
        self.safety_engine.safe_mode = self.safe_mode
        self.safety_engine.source_config_dir = self.source_config_dir
        tx_result: TransactionResult = self.safety_engine.execute(
            operation,
            confirmed=True,
            force_safe_mode=force_safe_mode,
        )

        return ApplyResult(
            success=tx_result.success,
            message=tx_result.message,
            scheme_id=scheme_id,
            backup_id=tx_result.backup_id,
            rolled_back=tx_result.rolled_back,
            is_dry_run=tx_result.is_dry_run,
            diff_preview=diff_text,
        )

    def restore_backup(
        self,
        backup_id: str,
        target_scheme_id: Optional[str] = None,
    ) -> tuple[bool, str]:
        """Restore configuration from a snapshot transactionally and notify session."""
        self.safety_engine.safe_mode = self.safe_mode
        self.safety_engine.source_config_dir = self.source_config_dir

        tx_result = self.safety_engine.restore_snapshot_transactionally(
            snap_id=backup_id,
            file_whitelist=["kdeglobals"],
            confirmed=True,
            force_safe_mode=False,
        )

        if not tx_result.success:
            return False, f"Failed to restore backup '{backup_id}': {tx_result.message}"

        # If target scheme ID is known and tool is available, re-run tool to notify running apps
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
