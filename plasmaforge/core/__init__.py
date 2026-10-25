"""PlasmaForge core logic, configuration, and system abstraction modules."""

from plasmaforge.core.config import AppConfig, get_config, save_config
from plasmaforge.core.system_info import SystemInfo, get_system_info
from plasmaforge.core.backup_manager import BackupManager, SnapshotMetadata
from plasmaforge.core.adapter_boundary import (
    IKdeConfigAdapter,
    DryRunAdapter,
    SandboxAdapter,
    SafetyViolationError,
    ConfigChange,
    ConfigChangeSet,
)

__all__ = [
    "AppConfig",
    "get_config",
    "save_config",
    "SystemInfo",
    "get_system_info",
    "BackupManager",
    "SnapshotMetadata",
    "IKdeConfigAdapter",
    "DryRunAdapter",
    "SandboxAdapter",
    "SafetyViolationError",
    "ConfigChange",
    "ConfigChangeSet",
]
