"""Unit tests for StoreController state, signals, async workers, and QML interactions."""

from unittest.mock import MagicMock
from pathlib import Path
import pytest
from PySide6.QtCore import QCoreApplication

from plasmaforge.controllers.store_controller import StoreController
from plasmaforge.core.global_theme_applier import GlobalThemeApplier, GlobalThemeApplyResult
from plasmaforge.core.store_client import CatalogQueryResult, KdeStoreClient, StoreThemeEntry
from plasmaforge.core.theme_installer import InstalledThemeInfo, ThemeInstaller


@pytest.fixture(scope="session")
def qcore_app():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def _create_mock_theme(theme_id: str, name: str, version: str = "1.0") -> StoreThemeEntry:
    return StoreThemeEntry(
        id=theme_id,
        name=name,
        version=version,
        author="Tester",
        summary="A test theme",
        description="Detailed description of test theme",
        detail_url=f"https://store.kde.org/p/{theme_id}",
        preview_url="https://images.pling.com/preview.png",
        preview_thumbnails=["https://images.pling.com/thumb.png"],
        preview_images=["https://images.pling.com/preview.png"],
        downloads=1500,
        score=95,
        primary_download_url="https://files.pling.com/download.tar.gz",
        primary_download_name=f"{name}.tar.gz",
        primary_download_size_kb=512,
        primary_download_md5="0123456789abcdef0123456789abcdef",
    )


def test_store_controller_initial_properties(qcore_app) -> None:
    """Verify initial properties exposed to QML."""
    ctrl = StoreController()
    assert ctrl.catalog == []
    assert ctrl.isLoading is False
    assert ctrl.errorMessage == ""
    assert ctrl.searchQuery == ""
    assert ctrl.sortMode == "down"
    assert ctrl.currentPage == 1
    assert ctrl.pageSize == 16
    assert ctrl.totalItems == 0
    assert ctrl.hasMore is False
    assert ctrl.selectedIndex == -1
    assert ctrl.selectedTheme == {}
    assert isinstance(ctrl.installedThemes, list)
    assert ctrl.isDownloading is False
    assert ctrl.showApplyConfirmDialog is False


def test_store_controller_catalog_loading(qcore_app) -> None:
    """Verify catalog loading and installed status annotation."""
    mock_client = MagicMock(spec=KdeStoreClient)
    item1 = _create_mock_theme("101", "Sweet KDE", "2.0")
    item2 = _create_mock_theme("102", "Nordic Theme", "1.5")
    mock_client.fetch_catalog.return_value = CatalogQueryResult(
        items=[item1, item2],
        total_items=2,
        page=1,
        page_size=16,
        has_more=False,
    )

    mock_installer = MagicMock(spec=ThemeInstaller)
    mock_inspector = MagicMock()
    # Simulate Sweet KDE being already installed with version 1.9 (update available!)
    mock_inspector.list_installed_themes.return_value = [
        InstalledThemeInfo(
            id="sweet-kde",
            name="Sweet KDE",
            path="/usr/share/plasma/look-and-feel/Sweet",
            version="1.9",
            author="eliverlara",
            description="Installed Sweet theme",
            is_user_installed=False,
        )
    ]
    mock_installer.inspector = mock_inspector

    ctrl = StoreController(store_client=mock_client, installer=mock_installer)
    ctrl.refreshInstalledThemes()

    # Emulate catalog loaded callback directly
    res = mock_client.fetch_catalog.return_value
    ctrl._on_catalog_loaded(res)

    assert len(ctrl.catalog) == 2
    assert ctrl.totalItems == 2
    assert ctrl.selectedIndex == 0

    # Verify update annotation on item1
    first_item = ctrl.catalog[0]
    assert first_item["name"] == "Sweet KDE"
    assert first_item["is_installed"] is True
    assert first_item["has_update"] is True

    # Verify uninstalled annotation on item2
    second_item = ctrl.catalog[1]
    assert second_item["name"] == "Nordic Theme"
    assert second_item["is_installed"] is False
    assert second_item["has_update"] is False


def test_store_controller_selection(qcore_app) -> None:
    """Verify theme selection by index and by ID."""
    mock_client = MagicMock(spec=KdeStoreClient)
    item1 = _create_mock_theme("101", "Theme One")
    item2 = _create_mock_theme("102", "Theme Two")

    ctrl = StoreController(store_client=mock_client)
    ctrl._on_catalog_loaded(CatalogQueryResult([item1, item2], 2, 1, 16, False))

    assert ctrl.selectedIndex == 0
    assert ctrl.selectedTheme.get("name") == "Theme One"

    ctrl.selectTheme(1)
    assert ctrl.selectedIndex == 1
    assert ctrl.selectedTheme.get("name") == "Theme Two"

    assert ctrl.selectThemeById("101") is True
    assert ctrl.selectedIndex == 0
    assert ctrl.selectedTheme.get("name") == "Theme One"


def test_store_controller_apply_dialog_flow(qcore_app) -> None:
    """Verify requesting and cancelling theme apply confirmation dialog."""
    mock_applier = MagicMock(spec=GlobalThemeApplier)
    mock_installer = MagicMock(spec=ThemeInstaller)
    mock_inspector = MagicMock()
    mock_inspector.list_installed_themes.return_value = [
        InstalledThemeInfo(
            id="org.sample.laf",
            name="Sample LAF",
            path="/home/user/.local/share/plasma/look-and-feel/org.sample.laf",
            version="1.0",
            author="Author",
            description="Description",
            is_user_installed=True,
        )
    ]
    mock_installer.inspector = mock_inspector

    mock_applier.analyze_theme_impact.return_value = (
        {"Color Scheme": "SampleColors"},
        ["kdeglobals", "plasmarc"],
        ["Icon theme missing note"],
    )
    mock_applier.generate_diff_preview.return_value = "# Diff Preview Content"

    ctrl = StoreController(installer=mock_installer, applier=mock_applier)
    ctrl.refreshInstalledThemes()

    ctrl.requestApplyTheme("org.sample.laf")
    assert ctrl.showApplyConfirmDialog is True
    assert ctrl.confirmThemeId == "org.sample.laf"
    assert ctrl.confirmThemeName == "Sample LAF"
    assert ctrl.confirmAffectedFiles == ["kdeglobals", "plasmarc"]
    assert ctrl.confirmWarnings == ["Icon theme missing note"]
    assert ctrl.currentDiffPreview == "# Diff Preview Content"

    ctrl.cancelApplyTheme()
    assert ctrl.showApplyConfirmDialog is False
    assert ctrl.confirmThemeId == ""
