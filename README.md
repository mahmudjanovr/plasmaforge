# PlasmaForge

> **Native Linux desktop customization studio for KDE Plasma 6 on Wayland.**

PlasmaForge is a high-performance, dark-first desktop customization studio engineered specifically for Arch Linux and KDE Plasma 6 running on Wayland. Built with Python, PySide6, and Qt Quick / QML, it provides a safe, responsive workspace optimized for native desktop performance on integrated graphics and 8 GB RAM systems.

---

## Architecture & Design (Phase 2)

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
│   │   ├── backup_manager.py       # Sandboxed cryptographic snapshots (SHA256 manifests & restore)
│   │   ├── themes.py               # Discovery, active scheme detection & palette parsing
│   │   ├── color_scheme_applier.py # Safe KDE color scheme applier with rollback & diff preview
│   │   └── presets.py              # Curated native desktop recipe catalog
│   ├── controllers/                # QML presentation singletons (PlasmaForge.Controllers 1.0)
│   │   ├── app_controller.py       # Active view navigation, safe mode, and status toasts
│   │   ├── system_controller.py    # Exposes system metrics & KDE tools to QML
│   │   ├── theme_controller.py     # Scheme selection, diff preview, confirmation & apply workflows
│   │   ├── preset_controller.py    # Gallery preset inspector & dry-run diffs
│   │   ├── backup_controller.py    # Snapshot creation, listing, integrity verification
│   │   └── settings_controller.py  # Preferences & dynamic safe mode toggle
│   └── qml/                        # Qt Quick presentation layer
│       ├── main.qml                # Main application window, sidebar shell & modal overlays
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
│           ├── ThemeStudioView.qml # Live color scheme inspector, diff drawer & apply confirmation
│           ├── DesktopBuilderView.qml
│           ├── SetupGalleryView.qml
│           ├── BackupRestoreView.qml
│           ├── SettingsView.qml    # Dynamic Safe Mode / Live Mode configuration
│           └── qmldir
└── tests/                          # Automated pytest suite (30 tests)
    ├── test_config.py
    ├── test_system_info.py
    ├── test_adapter_boundary.py
    ├── test_backup_manager.py
    ├── test_themes_and_presets.py
    ├── test_color_scheme_applier.py
    ├── test_controllers.py
    └── test_qml_loading.py
```

---

## Safety Foundation & Phase 2 Architecture

PlasmaForge is designed so that users never unknowingly mutate their live desktop:

- **Explicit Safe Mode (Default)**: Safe Mode is enabled by default. While active, all theme applications simulate changes, generating real unified diffs and verified snapshots without modifying live KDE configurations.
- **Pre-Apply Cryptographic Backups**: Before applying any scheme in Live Mode, PlasmaForge creates a full cryptographic snapshot of `kdeglobals` and verifies its SHA256 integrity on disk before executing any tool.
- **Strict Input Validation & Whitelisting**: Color scheme identifiers must match alphanumeric/standard name characters (`[a-zA-Z0-9_-]+`) and exist in the discovered installed schemes list.
- **No Shell Execution**: System commands are invoked strictly using vector arguments (`subprocess.run(["plasma-apply-colorscheme", scheme_id], shell=False)`) with a 15-second execution timeout.
- **Automatic Failure Rollback**: If `plasma-apply-colorscheme` exits non-zero or times out, the applier immediately rolls back `kdeglobals` from the verified pre-apply snapshot and reports a meaningful error.
- **One-Click Restore**: The UI retains the pre-apply snapshot ID and previous scheme name, allowing users to instantly restore their previous color scheme with SHA256 integrity verification.

---

## Navigation Sections

1. **Overview**:
   - Live system inspection: KDE Plasma version, Qt version, Wayland session type, active Look & Feel theme, and system fonts.
   - Real-time diagnostic indicators for core KDE Plasma 6 binaries (`plasmashell`, `plasma-apply-colorscheme`, `kwriteconfig6`, `kreadconfig6`, `qdbus6`).
   - Quick safety metrics, active mode status badge, and snapshot counts.

2. **Theme Studio**:
   - Live discovery of installed color schemes from `/usr/share/color-schemes/` and `~/.local/share/color-schemes/`.
   - Palette role swatches (Window BG/FG, View BG/FG, Selection, Buttons).
   - Dynamic Active Scheme detection (displays an "Active" badge and disables re-applying identical themes).
   - **Preview Changes (Diff)**: Slide-out drawer displaying an exact unified diff of `kdeglobals` prior to application.
   - **Confirmation Modal**: Clear in-window confirmation identifying the selected scheme, backup location, and active execution mode (Safe Mode vs Live Mode).
   - **Apply & Restore**: Apply color scheme via `plasma-apply-colorscheme`, with toast notifications and one-click restoration of the previous scheme.

3. **Desktop Builder**:
   - Interactive schematic preview of the primary Wayland display layout, taskbar, dock, and applet regions.
   - Staging workbench state: clearly informs the user that widget orchestration and panel restructuring are reserved for later phases.

4. **Setup Gallery**:
   - Curated native desktop presets: *Obsidian Teal Studio*, *Nordic Horizon*, *Arch Minimalist*, and *Paper & Umber Dark*.
   - Component breakdowns, palette swatches, and tagging.
   - Changeset Dry-Run Inspector: generates exact unified diffs of proposed configuration adjustments via the `DryRunAdapter`.

5. **Backups & Restore**:
   - Versioned snapshot creation of critical KDE Plasma configuration files.
   - List of stored snapshots with timestamp, file count, and size in KB.
   - Cryptographic SHA256 integrity verification tool.
   - Restore snapshots with safe file-whitelist validation and diff preview.

6. **Settings**:
   - **Safe Mode Toggle**: Clearly toggle between Safe Mode (simulated dry-run previews) and Live Mode (verified real KDE desktop modifications).
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
- Configuration parsing, default values, and dynamic safe mode toggling
- Safe system information detection and fallback behavior
- Adapter boundary validation, identifier whitelisting, and dry-run execution
- Backup snapshot creation, SHA256 integrity verification, and safe file restoration
- Color extraction, installed scheme discovery, and active scheme detection
- ColorSchemeApplier validation, diff preview generation, pre-apply snapshot creation, live execution, rollback on failure, and restore
- Controller state transitions, theme application workflow, and navigation signals
- Headless QML engine loading and view switching (30 tests passing)
