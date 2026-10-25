# PlasmaForge

> **Native Linux desktop customization studio for KDE Plasma 6 on Wayland.**

PlasmaForge is a high-performance, dark-first desktop customization studio engineered specifically for Arch Linux and KDE Plasma 6 running on Wayland. Built with Python, PySide6, and Qt Quick / QML, it provides a safe, responsive workspace optimized for native desktop performance on integrated graphics and 8 GB RAM systems.

---

## Architecture & Design (Phase 1)

PlasmaForge follows a strict separation of concerns between native presentation, application state, and configuration safety boundaries:

```
plasmaforge/
├── run.py                          # Single straightforward launcher
├── pyproject.toml                  # Project metadata and pytest configuration
├── plasmaforge/
│   ├── __init__.py
│   ├── main.py                     # Entrypoint & Qt Quick engine bootstrap
│   ├── core/                       # Core system logic & safety boundaries
│   │   ├── config.py               # XDG-compliant app configuration (~/.config/plasmaforge)
│   │   ├── system_info.py          # Read-only detection of KDE Plasma 6 and host environment
│   │   ├── adapter_boundary.py     # Safe configuration change contract & DryRunAdapter
│   │   ├── backup_manager.py       # Sandboxed cryptographic snapshots (SHA256 manifests)
│   │   ├── themes.py               # Discovery & palette parsing for installed color schemes
│   │   └── presets.py              # Curated native desktop recipe catalog
│   ├── controllers/                # QML presentation singletons (PlasmaForge.Controllers 1.0)
│   │   ├── app_controller.py       # Active view navigation and status toasts
│   │   ├── system_controller.py    # Exposes system metrics & KDE tools to QML
│   │   ├── theme_controller.py     # Color scheme selection & preview bindings
│   │   ├── preset_controller.py    # Gallery preset inspector & dry-run diffs
│   │   ├── backup_controller.py    # Snapshot creation, listing, integrity verification
│   │   └── settings_controller.py  # Preferences & safety mode enforcement
│   └── qml/                        # Qt Quick presentation layer
│       ├── main.qml                # Main application window & sidebar shell
│       ├── theme/                  # Design tokens singleton (dark-first, teal accents)
│       │   ├── Theme.qml
│       │   └── qmldir
│       ├── components/             # Reusable native-feel components
│       │   ├── PFButton.qml
│       │   ├── PFCard.qml
│       │   ├── PFBadge.qml
│       │   ├── PFMetricCard.qml
│       │   ├── PFSectionHeader.qml
│       │   ├── PFEmptyState.qml
│       │   ├── PFToast.qml
│       │   └── qmldir
│       └── views/                  # Section workspace views
│           ├── OverviewView.qml
│           ├── ThemeStudioView.qml
│           ├── DesktopBuilderView.qml
│           ├── SetupGalleryView.qml
│           ├── BackupRestoreView.qml
│           ├── SettingsView.qml
│           └── qmldir
└── tests/                          # Automated pytest suite (22 tests)
    ├── test_config.py
    ├── test_system_info.py
    ├── test_adapter_boundary.py
    ├── test_backup_manager.py
    ├── test_themes_and_presets.py
    ├── test_controllers.py
    └── test_qml_loading.py
```

---

## Safety Foundation

PlasmaForge Phase 1 is built around non-destructive, read-only principles:

- **Zero Unauthorized Modifications**: Direct writing to the user's live `~/.config` files is strictly blocked in Phase 1.
- **Strict Identifier Whitelisting**: Configuration modifications must target explicitly whitelisted KDE files (`kdeglobals`, `plasmarc`, `plasma-org.kde.plasma.desktop-appletsrc`, `kwinrc`, `kglobalshortcutsrc`). Newline injection and shell escapes are prevented by strict regex pattern validation.
- **DryRunAdapter Contract**: Preset applications generate unified diffs and previews without writing to disk. Attempting to apply live changes while `safe_mode` is active raises a `SafetyViolationError`.
- **Cryptographic Backups**: The snapshot engine creates versioned copies in `~/.local/share/plasmaforge/snapshots/` accompanied by a `manifest.json` containing SHA256 checksums. Restore checks run in dry-run mode to display differences against live configurations without altering them.

---

## Navigation Sections

1. **Overview**:
   - Live system inspection: KDE Plasma version, Qt version, Wayland session type, active Look & Feel theme, and system fonts.
   - Real-time diagnostic indicators for core KDE Plasma 6 binaries (`plasmashell`, `kwriteconfig6`, `kreadconfig6`, `qdbus6`).
   - Quick safety metrics and snapshot overview.

2. **Theme Studio**:
   - Safe inspection of installed color schemes from `/usr/share/color-schemes/` and `~/.local/share/color-schemes/`.
   - Live palette role swatches (Window BG/FG, View BG/FG, Selection, Buttons).
   - Discovery of installed Plasma desktop themes (desktop styles).
   - Realistic read-only staging indicator: explains safe inspection mode without pretending live edits take place.

3. **Desktop Builder**:
   - Interactive schematic preview of the primary Wayland display layout, taskbar, dock, and applet regions.
   - Staging workbench state: clearly informs the user that widget orchestration and panel restructuring are reserved for Phase 2 once adapter verification is certified.

4. **Setup Gallery**:
   - Curated native desktop presets: *Obsidian Teal Studio*, *Nordic Horizon*, *Arch Minimalist*, and *Paper & Umber Dark*.
   - Component breakdowns, palette swatches, and tagging.
   - Changeset Dry-Run Inspector: generates exact unified diffs of proposed configuration adjustments via the `DryRunAdapter`.

5. **Backups & Restore**:
   - Versioned snapshot creation of critical KDE Plasma configuration files.
   - List of stored snapshots with timestamp, file count, and size in KB.
   - Cryptographic SHA256 integrity verification tool.
   - Dry-Run Restore comparison: displays line-by-line diffs against live configuration files without touching filesystem state.

6. **Settings**:
   - Phase 1 Safety Mode: locked active with explanation.
   - Snapshot storage directory path configuration.
   - UI appearance mode (Dark / System Sync) and motion animation toggles.
   - Environment and adapter readiness diagnostics.

---

## Launch Instructions

### Prerequisites
- Linux (Arch Linux recommended)
- KDE Plasma 6 on Wayland or X11
- Python >= 3.11 with PySide6 and pytest installed

### Quick Start

Launch the application directly with the virtual environment:

```bash
# Development launch command
.venv/bin/python run.py
```

Or activate the environment and launch:

```bash
source .venv/bin/activate
python run.py
```

### CLI Flags

```bash
# Run headless offscreen startup validation
.venv/bin/python run.py --offscreen

# Print application version
.venv/bin/python run.py --version

# Show launcher help
.venv/bin/python run.py --help
```

---

## Automated Test Suite

Run the full pytest suite:

```bash
.venv/bin/pytest -v
```

The test suite validates:
- Configuration parsing, default values, and safe mode enforcement
- Safe system information detection and fallback behavior
- Adapter boundary validation, identifier whitelisting, and dry-run execution
- Backup snapshot creation, SHA256 integrity verification, and dry-run diffs
- Color extraction and preset validation
- Controller state transitions and navigation signals
- Headless QML engine loading and view switching
