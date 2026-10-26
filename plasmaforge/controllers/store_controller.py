"""Store controller coordinating remote KDE Global Themes browsing, safe download, and transactional application."""

from __future__ import annotations

import concurrent.futures
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from plasmaforge.core.config import get_config
from plasmaforge.core.global_theme_applier import (
    GlobalThemeApplier,
    GlobalThemeApplyResult,
)
from plasmaforge.core.store_client import (
    CatalogQueryResult,
    KdeStoreClient,
    StoreClientError,
    StoreNetworkError,
    StoreThemeEntry,
)
from plasmaforge.core.theme_installer import (
    InstalledThemeInfo,
    ThemeDownloader,
    ThemeInstaller,
    ThemePackageInspector,
)


class StoreSignals(QObject):
    """Thread-safe signal dispatcher for background worker tasks."""

    catalogLoaded = Signal(object)  # CatalogQueryResult
    catalogError = Signal(str)
    downloadProgress = Signal(int, int, float, str)  # bytes, total, percent, message
    downloadCompleted = Signal(bool, str, str)  # success, message, theme_id
    applyCompleted = Signal(bool, str, bool, str)  # success, message, is_dry_run, theme_id


class StoreController(QObject):
    """QML Singleton controller for browsing, searching, downloading, and safely applying KDE Global Themes."""

    catalogChanged = Signal()
    loadingChanged = Signal()
    errorChanged = Signal()
    selectedThemeChanged = Signal()
    installedThemesChanged = Signal()
    downloadProgressChanged = Signal()
    applyDialogStateChanged = Signal()
    operationCompleted = Signal(str, bool)  # message, success
    applyFinished = Signal(bool, str, bool)  # success, message, is_dry_run

    def __init__(
        self,
        parent: QObject | None = None,
        store_client: Optional[KdeStoreClient] = None,
        installer: Optional[ThemeInstaller] = None,
        applier: Optional[GlobalThemeApplier] = None,
    ) -> None:
        super().__init__(parent)
        self._config = get_config()

        self._store_client = store_client or KdeStoreClient()
        self._downloader = ThemeDownloader()
        self._installer = installer or ThemeInstaller(downloader=self._downloader)
        self._applier = applier or GlobalThemeApplier(safe_mode=self._config.safe_mode)
        self._inspector = self._installer.inspector

        # Catalog State
        self._catalog_items: List[StoreThemeEntry] = []
        self._total_items: int = 0
        self._current_page: int = 1
        self._page_size: int = 16
        self._has_more: bool = False
        self._search_query: str = ""
        self._sort_mode: str = "down"  # "down", "new", "high", "alpha"

        self._is_loading: bool = False
        self._error_message: str = ""

        # Selection State
        self._selected_index: int = -1
        self._selected_theme_data: Dict[str, Any] = {}

        # Installed themes tracking
        self._installed_themes: List[InstalledThemeInfo] = []
        self._installed_map: Dict[str, InstalledThemeInfo] = {}  # id -> info
        self._active_theme_id: str = "org.kde.breeze.desktop"

        # Download State
        self._is_downloading: bool = False
        self._download_theme_id: str = ""
        self._download_percent: float = 0.0
        self._download_status: str = ""

        # Apply Dialog State
        self._show_apply_dialog: bool = False
        self._confirm_theme_id: str = ""
        self._confirm_theme_name: str = ""
        self._confirm_affected_files: List[str] = []
        self._confirm_warnings: List[str] = []
        self._current_diff_preview: str = ""
        self._is_applying: bool = False

        # Threading infrastructure
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=3,
            thread_name_prefix="pf_store_",
        )
        self._signals = StoreSignals(self)
        self._wire_signals()

        # Initial state scan
        self.refreshInstalledThemes()

    def _wire_signals(self) -> None:
        """Connect thread-safe background signals to GUI handler methods."""
        self._signals.catalogLoaded.connect(self._on_catalog_loaded)
        self._signals.catalogError.connect(self._on_catalog_error)
        self._signals.downloadProgress.connect(self._on_download_progress)
        self._signals.downloadCompleted.connect(self._on_download_completed)
        self._signals.applyCompleted.connect(self._on_apply_completed)

    # ==========================================
    # Properties for QML
    # ==========================================
    @Property("QVariantList", notify=catalogChanged)
    def catalog(self) -> List[Dict[str, Any]]:
        return [item.to_dict() for item in self._catalog_items]

    @Property(bool, notify=loadingChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(str, notify=errorChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @Property(str, notify=catalogChanged)
    def searchQuery(self) -> str:
        return self._search_query

    @Property(str, notify=catalogChanged)
    def sortMode(self) -> str:
        return self._sort_mode

    @Property(int, notify=catalogChanged)
    def currentPage(self) -> int:
        return self._current_page

    @Property(int, notify=catalogChanged)
    def pageSize(self) -> int:
        return self._page_size

    @Property(int, notify=catalogChanged)
    def totalItems(self) -> int:
        return self._total_items

    @Property(bool, notify=catalogChanged)
    def hasMore(self) -> bool:
        return self._has_more

    @Property(int, notify=selectedThemeChanged)
    def selectedIndex(self) -> int:
        return self._selected_index

    @Property("QVariantMap", notify=selectedThemeChanged)
    def selectedTheme(self) -> Dict[str, Any]:
        return self._selected_theme_data

    @Property("QVariantList", notify=installedThemesChanged)
    def installedThemes(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._installed_themes]

    @Property(str, notify=installedThemesChanged)
    def activeThemeId(self) -> str:
        return self._active_theme_id

    @Property(bool, notify=downloadProgressChanged)
    def isDownloading(self) -> bool:
        return self._is_downloading

    @Property(str, notify=downloadProgressChanged)
    def downloadThemeId(self) -> str:
        return self._download_theme_id

    @Property(float, notify=downloadProgressChanged)
    def downloadPercent(self) -> float:
        return self._download_percent

    @Property(str, notify=downloadProgressChanged)
    def downloadStatus(self) -> str:
        return self._download_status

    @Property(bool, notify=applyDialogStateChanged)
    def showApplyConfirmDialog(self) -> bool:
        return self._show_apply_dialog

    @Property(str, notify=applyDialogStateChanged)
    def confirmThemeId(self) -> str:
        return self._confirm_theme_id

    @Property(str, notify=applyDialogStateChanged)
    def confirmThemeName(self) -> str:
        return self._confirm_theme_name

    @Property("QVariantList", notify=applyDialogStateChanged)
    def confirmAffectedFiles(self) -> List[str]:
        return self._confirm_affected_files

    @Property("QVariantList", notify=applyDialogStateChanged)
    def confirmWarnings(self) -> List[str]:
        return self._confirm_warnings

    @Property(str, notify=applyDialogStateChanged)
    def currentDiffPreview(self) -> str:
        return self._current_diff_preview

    @Property(bool, notify=applyDialogStateChanged)
    def isApplying(self) -> bool:
        return self._is_applying

    # ==========================================
    # Asynchronous Catalog Fetching
    # ==========================================
    @Slot()
    def loadCatalog(self) -> None:
        """Start asynchronous fetch of the global themes catalog."""
        self._is_loading = True
        self._error_message = ""
        self.loadingChanged.emit()
        self.errorChanged.emit()

        query = self._search_query
        page = self._current_page
        psize = self._page_size
        sort = self._sort_mode

        def worker() -> None:
            try:
                res = self._store_client.fetch_catalog(
                    search_query=query,
                    page=page,
                    page_size=psize,
                    sort_mode=sort,
                )
                self._signals.catalogLoaded.emit(res)
            except StoreNetworkError as e:
                self._signals.catalogError.emit(f"Network error connecting to KDE Store: {e}")
            except StoreClientError as e:
                self._signals.catalogError.emit(f"KDE Store error: {e}")
            except Exception as e:
                self._signals.catalogError.emit(f"Unexpected error querying store: {e}")

        self._executor.submit(worker)

    def _on_catalog_loaded(self, res: CatalogQueryResult) -> None:
        """Handle successful catalog query on the GUI thread."""
        self._catalog_items = res.items
        self._total_items = res.total_items
        self._has_more = res.has_more
        self._is_loading = False
        self._error_message = ""

        # Sync installed status on catalog items
        self._annotate_installed_status()

        # Update selected theme if in range
        if 0 <= self._selected_index < len(self._catalog_items):
            self._update_selected_theme(self._catalog_items[self._selected_index])
        elif self._catalog_items:
            self._selected_index = 0
            self._update_selected_theme(self._catalog_items[0])
        else:
            self._selected_index = -1
            self._update_selected_theme(None)

        self.loadingChanged.emit()
        self.errorChanged.emit()
        self.catalogChanged.emit()
        self.selectedThemeChanged.emit()

    def _on_catalog_error(self, err_msg: str) -> None:
        """Handle catalog fetch failure on the GUI thread."""
        self._is_loading = False
        self._error_message = err_msg
        self.loadingChanged.emit()
        self.errorChanged.emit()
        self.operationCompleted.emit(err_msg, False)

    def _annotate_installed_status(self) -> None:
        """Check catalog items against installed themes."""
        for item in self._catalog_items:
            inst = self._find_installed_match(item)
            if inst:
                item.is_installed = True
                item.installed_version = inst.version
                # Flag update if store version is different
                item.has_update = bool(
                    item.version and inst.version and item.version.strip() != inst.version.strip()
                )
            else:
                item.is_installed = False
                item.installed_version = ""
                item.has_update = False

    def _find_installed_match(self, item: StoreThemeEntry) -> Optional[InstalledThemeInfo]:
        """Find matching installed theme by package id, name, or primary download archive name."""
        # 1. Match by exact ID or lowercase ID
        if item.id in self._installed_map:
            return self._installed_map[item.id]

        item_id_lower = item.id.lower()
        item_name_lower = item.name.lower().strip()

        # Try stripping archive extensions from primary download name
        archive_stem = ""
        if item.primary_download_name:
            clean = item.primary_download_name
            for ext in (".tar.gz", ".tar.xz", ".tgz", ".zip", ".tar.bz2"):
                if clean.lower().endswith(ext):
                    clean = clean[: -len(ext)]
                    break
            archive_stem = clean.lower()

        for inst in self._installed_themes:
            inst_id = inst.id.lower()
            inst_name = inst.name.lower()
            if inst_id == item_id_lower or inst_name == item_name_lower:
                return inst
            if archive_stem and (inst_id == archive_stem or archive_stem in inst_id or inst_id in archive_stem):
                return inst

        return None

    # ==========================================
    # Installed Themes State
    # ==========================================
    @Slot()
    def refreshInstalledThemes(self) -> None:
        """Scan system and user paths for installed Look and Feel packages."""
        self._active_theme_id = self._applier.detect_active_theme_id()
        self._installed_themes = self._inspector.list_installed_themes(active_id=self._active_theme_id)
        self._installed_map = {t.id: t for t in self._installed_themes}

        self._annotate_installed_status()
        self.installedThemesChanged.emit()
        self.catalogChanged.emit()

    @Slot(str, result=bool)
    def isThemeInstalled(self, theme_id: str) -> bool:
        """Check if a given theme ID or name is installed."""
        if not theme_id:
            return False
        clean = theme_id.lower().strip()
        for t in self._installed_themes:
            if t.id.lower() == clean or t.name.lower() == clean:
                return True
        return False

    # ==========================================
    # Search, Sorting & Pagination Slots
    # ==========================================
    @Slot(str)
    def search(self, query: str) -> None:
        """Search store catalog by query string."""
        clean = query.strip()
        if self._search_query != clean:
            self._search_query = clean
            self._current_page = 1
            self.loadCatalog()

    @Slot(str)
    def setSortMode(self, mode: str) -> None:
        """Change catalog sorting criteria."""
        if mode in ("down", "new", "high", "alpha") and self._sort_mode != mode:
            self._sort_mode = mode
            self._current_page = 1
            self.loadCatalog()

    @Slot(int)
    def goToPage(self, page: int) -> None:
        """Navigate to specific page."""
        if page >= 1 and page != self._current_page:
            self._current_page = page
            self.loadCatalog()

    @Slot()
    def nextPage(self) -> None:
        if self._has_more:
            self.goToPage(self._current_page + 1)

    @Slot()
    def previousPage(self) -> None:
        if self._current_page > 1:
            self.goToPage(self._current_page - 1)

    # ==========================================
    # Selection Slots
    # ==========================================
    @Slot(int)
    def selectTheme(self, index: int) -> None:
        """Select a theme from the current catalog page by index."""
        if 0 <= index < len(self._catalog_items):
            self._selected_index = index
            self._update_selected_theme(self._catalog_items[index])
            self.selectedThemeChanged.emit()

    @Slot(str, result=bool)
    def selectThemeById(self, theme_id: str) -> bool:
        """Select a theme by its store ID."""
        for idx, item in enumerate(self._catalog_items):
            if item.id == theme_id:
                self.selectTheme(idx)
                return True
        return False

    def _update_selected_theme(self, item: Optional[StoreThemeEntry]) -> None:
        """Update selected theme dictionary for QML bindings."""
        if item is None:
            self._selected_theme_data = {}
            return

        d = item.to_dict()
        inst = self._find_installed_match(item)
        if inst:
            d["is_installed"] = True
            d["installed_id"] = inst.id
            d["installed_version"] = inst.version
            d["installed_path"] = inst.path
            d["components"] = inst.components
            d["is_active"] = (
                self._active_theme_id.lower() == inst.id.lower()
                or self._active_theme_id.lower() == inst.name.lower()
            )
        else:
            d["is_installed"] = False
            d["installed_id"] = ""
            d["installed_version"] = ""
            d["installed_path"] = ""
            d["components"] = {}
            d["is_active"] = False

        self._selected_theme_data = d

    # ==========================================
    # Download & Installation Workflow
    # ==========================================
    @Slot(str)
    def startInstallTheme(self, theme_id: str) -> None:
        """Start downloading and installing a theme asynchronously."""
        if self._is_downloading:
            self.operationCompleted.emit("Another download is currently in progress.", False)
            return

        target_item = next((item for item in self._catalog_items if item.id == theme_id), None)
        if not target_item:
            # Check selected
            if self._selected_theme_data and str(self._selected_theme_data.get("id")) == theme_id:
                # Find download url
                dl_url = str(self._selected_theme_data.get("primary_download_url", ""))
                dl_md5 = str(self._selected_theme_data.get("primary_download_md5", ""))
            else:
                self.operationCompleted.emit(f"Theme '{theme_id}' was not found in catalog.", False)
                return
        else:
            dl_url = target_item.primary_download_url
            dl_md5 = target_item.primary_download_md5

        if not dl_url:
            self.operationCompleted.emit("No download package URL available for this theme.", False)
            return

        self._is_downloading = True
        self._download_theme_id = theme_id
        self._download_percent = 0.0
        self._download_status = "Connecting to KDE Store CDN..."
        self.downloadProgressChanged.emit()

        def progress_cb(b_read: int, b_total: int, pct: float, msg: str) -> None:
            self._signals.downloadProgress.emit(b_read, b_total, pct, msg)

        def worker() -> None:
            ok, msg, installed_info = self._installer.download_and_install(
                download_url=dl_url,
                expected_md5=dl_md5,
                theme_id=theme_id,
                progress_callback=progress_cb,
            )
            self._signals.downloadCompleted.emit(ok, msg, theme_id)

        self._executor.submit(worker)

    @Slot()
    def cancelDownload(self) -> None:
        """Cancel ongoing download immediately."""
        if self._is_downloading:
            self._downloader.cancel()
            self._is_downloading = False
            self._download_status = "Download cancelled."
            self.downloadProgressChanged.emit()
            self.operationCompleted.emit("Theme download cancelled.", False)

    def _on_download_progress(self, b_read: int, b_total: int, pct: float, msg: str) -> None:
        """Update progress on the GUI thread."""
        self._download_percent = pct
        self._download_status = msg
        self.downloadProgressChanged.emit()

    def _on_download_completed(self, success: bool, message: str, theme_id: str) -> None:
        """Handle download and installation finish on the GUI thread."""
        self._is_downloading = False
        self._download_theme_id = ""
        self._download_percent = 100.0 if success else 0.0
        self._download_status = message
        self.downloadProgressChanged.emit()

        if success:
            self.refreshInstalledThemes()
            # Reselect theme to refresh its installed status
            if self._selected_theme_data and str(self._selected_theme_data.get("id")) == theme_id:
                if 0 <= self._selected_index < len(self._catalog_items):
                    self._update_selected_theme(self._catalog_items[self._selected_index])
                    self.selectedThemeChanged.emit()

        self.operationCompleted.emit(message, success)

    @Slot(str)
    def uninstallTheme(self, theme_id: str) -> None:
        """Safely uninstall a user-installed Look and Feel theme."""
        ok, msg = self._installer.uninstall_theme(theme_id)
        self.operationCompleted.emit(msg, ok)
        if ok:
            self.refreshInstalledThemes()

    # ==========================================
    # Transactional Application Workflow
    # ==========================================
    @Slot(str)
    def requestApplyTheme(self, theme_id: str) -> None:
        """Inspect target theme and open explicit confirmation dialog with impact analysis and diff."""
        # Find installed theme
        inst = self._find_installed_by_id_or_name(theme_id)
        if not inst:
            self.operationCompleted.emit(
                f"Global Theme '{theme_id}' must be installed before applying.",
                False,
            )
            return

        components, affected_files, warnings = self._applier.analyze_theme_impact(inst)
        diff_text = self._applier.generate_diff_preview(inst)

        self._confirm_theme_id = inst.id
        self._confirm_theme_name = inst.name
        self._confirm_affected_files = affected_files
        self._confirm_warnings = warnings
        self._current_diff_preview = diff_text
        self._show_apply_dialog = True
        self.applyDialogStateChanged.emit()

    @Slot()
    def cancelApplyTheme(self) -> None:
        """Dismiss application confirmation dialog."""
        self._show_apply_dialog = False
        self._confirm_theme_id = ""
        self._confirm_theme_name = ""
        self._confirm_affected_files = []
        self._confirm_warnings = []
        self._current_diff_preview = ""
        self.applyDialogStateChanged.emit()

    @Slot()
    def confirmApplyTheme(self) -> None:
        """Execute transactional application of confirmed theme."""
        theme_id = self._confirm_theme_id
        if not theme_id:
            return

        self._show_apply_dialog = False
        self._is_applying = True
        self.applyDialogStateChanged.emit()

        # Update latest safe mode setting
        config = get_config()
        self._applier.safe_mode = config.safe_mode

        def worker() -> None:
            res: GlobalThemeApplyResult = self._applier.apply_theme(theme_id)
            self._signals.applyCompleted.emit(
                res.success,
                res.message,
                res.is_dry_run,
                theme_id,
            )

        self._executor.submit(worker)

    def _on_apply_completed(self, success: bool, message: str, is_dry_run: bool, theme_id: str) -> None:
        """Handle application finish on the GUI thread."""
        self._is_applying = False
        self._confirm_theme_id = ""
        self.applyDialogStateChanged.emit()

        if success and not is_dry_run:
            self.refreshInstalledThemes()

        self.applyFinished.emit(success, message, is_dry_run)
        self.operationCompleted.emit(message, success)

    def _find_installed_by_id_or_name(self, theme_id: str) -> Optional[InstalledThemeInfo]:
        """Find installed theme matching ID or name."""
        clean = theme_id.lower().strip()
        for inst in self._installed_themes:
            if inst.id.lower() == clean or inst.name.lower() == clean:
                return inst
        return None
