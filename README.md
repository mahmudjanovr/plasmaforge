# PlasmaForge

> **Native Linux desktop customization studio for KDE Plasma 6 on Wayland.**

PlasmaForge is a high-performance, dark-first desktop customization studio engineered specifically for Arch Linux and KDE Plasma 6 running on Wayland. Built with Python, PySide6, and Qt Quick / QML, it provides a safe, responsive workspace optimized for native desktop performance on integrated graphics and 8 GB RAM systems.

---

## Architecture & Design (Phase 3)

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
│   │   ├── transaction.py          # Reusable transactional safety layer, states & rollback engine
│   │   ├── color_scheme_applier.py # KDE color scheme applier backed by TransactionalSafetyEngine
│   │   ├── desktop_layout.py       # Desktop layout model, detection, presets & layout applier
│   │   └── presets.py              # Curated native desktop recipe catalog
│   ├── controllers/                # QML presentation singletons (PlasmaForge.Controllers 1.0)
│   │   ├── app_controller.py       # Active view navigation, safe mode, and status toasts
│   │   ├── system_controller.py    # Exposes system metrics & KDE tools to QML
│   │   ├── theme_controller.py     # Scheme selection, diff preview, confirmation & apply workflows
│   │   ├── desktop_controller.py   # Desktop Builder draft workbench, presets, diffs & safe apply
│   │   ├── preset_controller.py    # Gallery preset inspector & dry-run diffs
│   │   ├── backup_controller.py    # Snapshot creation, listing, integrity verification & safe restore
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
│           ├── DesktopBuilderView.qml# Interactive desktop layout blueprint & workbench
│           ├── SetupGalleryView.qml
│           ├── BackupRestoreView.qml# Snapshot manager & transactional restore modal
│           ├── SettingsView.qml    # Dynamic Safe Mode / Live Mode configuration
│           └── qmldir
└── tests/                          # Automated pytest suite (51 tests)
    ├── test_config.py
    ├── test_system_info.py
    ├── test_adapter_boundary.py
    ├── test_backup_manager.py
    ├── test_themes_and_presets.py
    ├── test_color_scheme_applier.py
    ├── test_transaction_safety.py  # 12 focused transactional apply & rollback tests
    ├── test_desktop_builder.py     # 8 focused Desktop Builder models, presets & apply tests
    ├── test_controllers.py         # App, theme, settings, preset, and desktop controller workflows
    └── test_qml_loading.py
```

---

## Phase 3 & 4 Transactional Safety Engine

PlasmaForge enforces a reusable, transactional safety boundary across all customization operations:

1. **Target Allowlisting & Path Sanitization**:
   - Only allowlisted KDE configuration files (`kdeglobals`, `plasmarc`, `plasma-org.kde.plasma.desktop-appletsrc`, `kwinrc`, `kglobalshortcutsrc`) located within the user's configuration root can be targeted.
   - Any attempt to target non-allowlisted files or traverse directories (`../../etc/shadow`) is strictly rejected during validation.

2. **Unified 6-Stage Apply Workflow**:
   - **Stage 1 (Validation & Preview)**: Validates target files, prerequisites, and computes exact unified diffs.
   - **Stage 2 (Safe Mode Check)**: Safe Mode is enabled by default. In Safe Mode, operations generate simulated diffs and test snapshots without modifying live system files.
   - **Stage 3 (Pre-Apply Cryptographic Backup)**: In Live Mode, an automatic snapshot is created and its SHA256 hashes are verified on disk before any mutation is attempted. If backup verification fails, the operation aborts immediately.
   - **Stage 4 (Explicit Confirmation)**: Live Mode strictly requires explicit user confirmation via an in-window modal before touching live files.
   - **Stage 5 (Safe Execution)**: System utilities and configuration modifications are executed safely using argument vectors (`shell=False`) or atomic config writes with execution timeouts. `plasmashell` is never terminated or killed automatically.
   - **Stage 6 (Post-Apply Verification & Rollback)**: Success is never reported before verification. If writing fails or post-apply verification fails, the engine automatically rolls back `~/.config` to the pre-apply snapshot.

3. **Safe Manual Snapshot Restoration**:
   - Snapshot manifests and file SHA256 hashes are verified before restoring. Corrupted or tampered snapshots are refused with clear error explanations.
   - An automatic pre-restore safety snapshot of the live configuration is created before writing restored files.
   - Post-restore verification verifies that restored files match the snapshot hashes.

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
   - **Confirmation Modal**: Clear in-window confirmation identifying the selected scheme, backup location, active mode, and safety pipeline badges.
   - **Apply & Restore**: Apply color scheme via `plasma-apply-colorscheme` backed by the `TransactionalSafetyEngine`, with toast notifications and one-click restoration of the previous scheme.

3. **Desktop Builder**:
   - **Visual 16:9 Display Blueprint**: Interactive representation of current Wayland display output with dynamic rendering of top panel, floating dock, and Nothing-inspired widgets.
   - **Live Detected vs Editable Draft**: Clearly communicates active detected geometry vs in-memory draft vs applied configuration.
   - **Sensible Presets**: Includes *Classic KDE* (conventional single bottom taskbar), *Nothing-Inspired* (minimal top status bar + centered bottom dock + widgets), and *Clean Minimal* (auto-hiding distraction-free workspace).
   - **Granular Controls**: Panel position (top, bottom, none), thickness (24–64px), visibility mode (always visible, auto-hide, dodge windows), dock position, dock thickness, dock icon size, and widget toggles.
   - **Live-Applicable vs Preview-Only Properties**:
     - *Live-Applicable*: Panel edge anchor position, thickness, visibility mode, dock edge position (written to `~/.config/plasma-org.kde.plasma.desktop-appletsrc` and verified).
     - *Preview-Only Simulation*: Custom desktop widget placement coordinates and floating dock margin padding (honestly labeled as visual simulations).
   - **Safe Apply & Rollback**: Uses `TransactionalSafetyEngine` with pre-apply backup, explicit confirmation, diff preview, verification, and one-click restore. `plasmashell` is never killed.

4. **Setup Gallery**:
   - Curated native desktop presets: *Obsidian Teal Studio*, *Nordic Horizon*, *Arch Minimalist*, and *Paper & Umber Dark*.
   - Component breakdowns, palette swatches, and tagging.
   - Changeset Dry-Run Inspector: generates exact unified diffs of proposed configuration adjustments via the `DryRunAdapter`.

5. **Backups & Restore**:
   - Versioned snapshot creation of critical KDE Plasma configuration files with unique monotonic identifiers.
   - List of stored snapshots with timestamp, file count, and size in KB.
   - Cryptographic SHA256 integrity verification tool.
   - **Transactional Restore**: In-window confirmation modal, pre-restore safety snapshot, SHA256 verification, and live restoration.

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
- Backup snapshot creation, unique monotonic snapshot IDs, and SHA256 integrity verification
- Color extraction, installed scheme discovery, and active scheme detection
- ColorSchemeApplier refactoring with transactional safety delegation
- Reusable TransactionalSafetyEngine: happy path, apply failure rollback, verification failure rollback, backup corruption abort, rollback failure handling, safe mode protection, unconfirmed live mode protection, and unsafe target rejection (12 focused tests)
- Safe manual snapshot restoration with pre-restore safety snapshot and post-restore SHA256 verification
- Controller state transitions, theme application workflow, and backup restore modal transitions
- Headless QML engine loading and view switching (42 tests passing)

---

## Known Real-World Limitations

- **Session Context**: Real-time theme notifications rely on the running KDE Plasma session and DBus. In isolated headless or mock environments without a running `plasmashell`, configuration files are safely updated on disk, but live broadcast events will not be received by external windows.
- **Scope Restriction**: PlasmaForge Phase 3 exclusively manages allowlisted desktop configurations (`kdeglobals`, `plasmarc`, `plasma-org.kde.plasma.desktop-appletsrc`, `kwinrc`, `kglobalshortcutsrc`). It intentionally does not touch non-KDE user configurations (e.g. bashrc, browser data, desktop files).
- **Rollback Guarantees**: Automatic rollback guarantees exact byte-for-byte restoration of allowlisted configuration files verified by SHA256 checksums. It cannot revert external side-effects produced by third-party processes outside KDE configuration files.
