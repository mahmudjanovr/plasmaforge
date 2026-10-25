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

from plasmaforge.core.color_scheme_applier import KdeColorSchemeApplier, ApplyResult
from plasmaforge.core.transaction import (
    ApplyOperation,
    TransactionalSafetyEngine,
    TransactionResult,
    TransactionState,
)
from plasmaforge.core.desktop_layout import (
    DesktopLayout,
    DesktopLayoutApplier,
    PanelConfig,
    detect_desktop_layout,
    get_layout_presets,
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
    "KdeColorSchemeApplier",
    "ApplyResult",
    "ApplyOperation",
    "TransactionalSafetyEngine",
    "TransactionResult",
    "TransactionState",
    "DesktopLayout",
    "DesktopLayoutApplier",
    "PanelConfig",
    "detect_desktop_layout",
    "get_layout_presets",
]
