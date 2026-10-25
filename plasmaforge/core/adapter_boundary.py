"""Safety boundary and adapter interfaces for KDE Plasma 6 configuration.

This module guarantees that no direct or unvalidated shell execution or
destructive configuration writes can occur. All modifications must flow
through typed change sets validated by an IKdeConfigAdapter implementation.
"""

from __future__ import annotations

import configparser
import difflib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


class SafetyViolationError(RuntimeError):
    """Raised when an operation attempts to bypass Phase 1 safety constraints."""


# Whitelist of allowed configuration targets in KDE Plasma
ALLOWED_CONFIG_FILES = {
    "kdeglobals": Path.home() / ".config" / "kdeglobals",
    "plasmarc": Path.home() / ".config" / "plasmarc",
    "plasma-org.kde.plasma.desktop-appletsrc": (
        Path.home() / ".config" / "plasma-org.kde.plasma.desktop-appletsrc"
    ),
    "kwinrc": Path.home() / ".config" / "kwinrc",
    "kglobalshortcutsrc": Path.home() / ".config" / "kglobalshortcutsrc",
}

# Identifier validation pattern to prevent injection
SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_:\-.]+$")


@dataclass
class ConfigChange:
    """Individual configuration key change."""

    file_identifier: str
    group: str
    key: str
    new_value: str
    old_value: Optional[str] = None
    reason: str = ""

    def validate(self) -> List[str]:
        """Validate safety of identifiers."""
        errors: List[str] = []
        if self.file_identifier not in ALLOWED_CONFIG_FILES:
            errors.append(
                f"File identifier '{self.file_identifier}' is not in the allowed KDE config whitelist."
            )
        if not SAFE_IDENTIFIER_PATTERN.match(self.group):
            errors.append(f"Invalid group identifier: '{self.group}'")
        if not SAFE_IDENTIFIER_PATTERN.match(self.key):
            errors.append(f"Invalid key identifier: '{self.key}'")
        # Reject newlines in values to prevent config section injection
        if "\n" in self.new_value or "\r" in self.new_value:
            errors.append("Config value must not contain newline characters.")
        return errors


@dataclass
class ConfigChangeSet:
    """Group of configuration changes applied together."""

    name: str
    description: str
    changes: List[ConfigChange] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def validate(self) -> List[str]:
        all_errors: List[str] = []
        for change in self.changes:
            all_errors.extend(change.validate())
        return all_errors


class IKdeConfigAdapter(ABC):
    """Abstract interface for KDE configuration manipulation."""

    @abstractmethod
    def validate(self, changeset: ConfigChangeSet) -> List[str]:
        """Return list of validation errors, or empty list if valid."""

    @abstractmethod
    def preview(self, changeset: ConfigChangeSet) -> str:
        """Generate a unified diff or formatted preview of changes without applying them."""

    @abstractmethod
    def apply(self, changeset: ConfigChangeSet) -> bool:
        """Apply changes. In Phase 1, live write is forbidden and raises SafetyViolationError."""


class DryRunAdapter(IKdeConfigAdapter):
    """Default adapter for Phase 1. Generates diffs but strictly forbids live writes."""

    def __init__(self, safe_mode: bool = True) -> None:
        self.safe_mode = safe_mode

    def validate(self, changeset: ConfigChangeSet) -> List[str]:
        return changeset.validate()

    def preview(self, changeset: ConfigChangeSet) -> str:
        errors = self.validate(changeset)
        if errors:
            return "VALIDATION FAILED:\n" + "\n".join(f"- {e}" for e in errors)

        lines: List[str] = [
            f"# Dry-Run Preview: {changeset.name}",
            f"# Description: {changeset.description}",
            f"# Generated: {changeset.created_at}",
            f"# Mode: SAFE / DRY-RUN (Zero filesystem modifications)",
            "--------------------------------------------------",
        ]

        # Group by file
        by_file: dict[str, list[ConfigChange]] = {}
        for c in changeset.changes:
            by_file.setdefault(c.file_identifier, []).append(c)

        for file_id, changes in by_file.items():
            lines.append(f"\nTarget File: ~/.config/{file_id}")
            for c in changes:
                old_val = c.old_value if c.old_value is not None else "(unset)"
                lines.append(f"  [{c.group}]")
                lines.append(f"    - {c.key} = {old_val}")
                lines.append(f"    + {c.key} = {c.new_value}")
                if c.reason:
                    lines.append(f"      reason: {c.reason}")

        return "\n".join(lines)

    def apply(self, changeset: ConfigChangeSet) -> bool:
        if self.safe_mode:
            raise SafetyViolationError(
                "Phase 1 Safety Mode Active: Live KDE configuration modification is strictly disabled. "
                "All operations must use preview or dry-run."
            )
        return False


class SandboxAdapter(IKdeConfigAdapter):
    """Test and simulation adapter that writes exclusively to an isolated temporary sandbox directory."""

    def __init__(self, sandbox_root: Path) -> None:
        self.sandbox_root = sandbox_root
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    def _resolve_sandbox_file(self, file_id: str) -> Path:
        target = (self.sandbox_root / file_id).resolve()
        if not str(target).startswith(str(self.sandbox_root.resolve())):
            raise SafetyViolationError(
                f"Path traversal detected: {file_id} escapes sandbox root."
            )
        return target

    def validate(self, changeset: ConfigChangeSet) -> List[str]:
        return changeset.validate()

    def preview(self, changeset: ConfigChangeSet) -> str:
        diff_outputs: List[str] = []
        for c in changeset.changes:
            target_path = self._resolve_sandbox_file(c.file_identifier)
            original_content = ""
            if target_path.is_file():
                original_content = target_path.read_text(encoding="utf-8")

            # Parse copy
            cfg = configparser.ConfigParser(interpolation=None)
            cfg.optionxform = str
            if original_content:
                cfg.read_string(original_content)

            if not cfg.has_section(c.group):
                cfg.add_section(c.group)
            cfg.set(c.group, c.key, c.new_value)

            import io
            buf = io.StringIO()
            cfg.write(buf)
            new_content = buf.getvalue()

            diff = list(
                difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f"a/{c.file_identifier}",
                    tofile=f"b/{c.file_identifier}",
                )
            )
            if diff:
                diff_outputs.append("".join(diff))
            else:
                diff_outputs.append(f"No changes in {c.file_identifier}")

        return "\n".join(diff_outputs)

    def apply(self, changeset: ConfigChangeSet) -> bool:
        errors = self.validate(changeset)
        if errors:
            raise ValueError(f"Cannot apply invalid changeset: {errors}")

        for c in changeset.changes:
            target_path = self._resolve_sandbox_file(c.file_identifier)
            cfg = configparser.ConfigParser(interpolation=None)
            cfg.optionxform = str
            if target_path.is_file():
                cfg.read(target_path, encoding="utf-8")

            if not cfg.has_section(c.group):
                cfg.add_section(c.group)
            cfg.set(c.group, c.key, c.new_value)

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                cfg.write(f)

        return True
