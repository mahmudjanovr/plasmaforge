"""KDE Store / OCS v1 API client for browsing KDE Global Themes.

Connects to the official KDE Store / OCS provider (api.kde-look.org) defined in
/usr/share/knsrcfiles/lookandfeel.knsrc to query live Plasma 6 Global Themes.
Supports search, pagination, sorting, metadata parsing, and honest error handling.
"""

from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


DEFAULT_OCS_PROVIDER_URL = "https://api.kde-look.org/ocs/v1"
DEFAULT_CATEGORY_ID = 722  # Global Themes (Plasma 6)
DEFAULT_TIMEOUT_SECONDS = 15.0
USER_AGENT = "PlasmaForge/1.0 (KDE Plasma 6 Customization Studio; Linux)"

HTML_TAG_CLEANER = re.compile(r"<[^>]+>")


class StoreClientError(RuntimeError):
    """Base error for KDE Store API operations."""


class StoreNetworkError(StoreClientError):
    """Raised on connection timeout or network transport failures."""


class StoreResponseError(StoreClientError):
    """Raised when the OCS provider returns a non-200 or invalid status payload."""


@dataclass
class ThemeDownloadItem:
    """Download item / archive option associated with a store theme."""

    index: int
    name: str
    url: str
    size_kb: int = 0
    md5: str = ""
    version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StoreThemeEntry:
    """Catalog entry representing a KDE Global Theme from the store."""

    id: str
    name: str
    version: str
    author: str
    summary: str
    description: str
    detail_url: str
    preview_url: str
    preview_thumbnails: List[str] = field(default_factory=list)
    preview_images: List[str] = field(default_factory=list)
    downloads: int = 0
    score: int = 0
    created_at: str = ""
    updated_at: str = ""
    download_items: List[ThemeDownloadItem] = field(default_factory=list)
    primary_download_url: str = ""
    primary_download_name: str = ""
    primary_download_size_kb: int = 0
    primary_download_md5: str = ""
    is_installed: bool = False
    installed_version: str = ""
    has_update: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["download_items"] = [item.to_dict() for item in self.download_items]
        return d


@dataclass
class CatalogQueryResult:
    """Result of a paginated search or browse query against the catalog."""

    items: List[StoreThemeEntry]
    total_items: int
    page: int
    page_size: int
    has_more: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "total_items": self.total_items,
            "page": self.page,
            "page_size": self.page_size,
            "has_more": self.has_more,
        }


def _strip_html(text: str) -> str:
    """Convert HTML snippet to plain text, stripping tags and unescaping entities."""
    if not text:
        return ""
    # Replace breaks/paragraphs with newlines
    normalized = text.replace("<br />", "\n").replace("<br/>", "\n").replace("<br>", "\n")
    normalized = normalized.replace("</p>", "\n\n").replace("</div>", "\n")
    clean = HTML_TAG_CLEANER.sub("", normalized)
    unescaped = html.unescape(clean)
    # Collapse 3+ consecutive newlines to 2
    return re.sub(r"\n{3,}", "\n\n", unescaped).strip()


class KdeStoreClient:
    """HTTP client for querying the official KDE Store / OCS v1 REST service."""

    def __init__(
        self,
        base_url: str = DEFAULT_OCS_PROVIDER_URL,
        category_id: int = DEFAULT_CATEGORY_ID,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.category_id = category_id
        self.timeout = timeout

    def _build_request(self, url: str) -> urllib.request.Request:
        """Construct standard HTTP request with headers."""
        return urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json, application/xml;q=0.9, */*;q=0.8",
            },
        )

    def fetch_catalog(
        self,
        search_query: str = "",
        page: int = 1,
        page_size: int = 16,
        sort_mode: str = "down",
    ) -> CatalogQueryResult:
        """Query global themes catalog from KDE store.

        Args:
            search_query: Search term (e.g. theme name, author, style).
            page: 1-indexed page number.
            page_size: Number of items per page.
            sort_mode: Sorting mode ('down' = downloads, 'new' = newest, 'high' = rating, 'alpha' = name).
        """
        # Map 1-based page to OCS page (OCS handles 0 and 1 as first page; pass page - 1 or page)
        ocs_page = max(0, page - 1)
        params: Dict[str, str] = {
            "categories": str(self.category_id),
            "pagesize": str(max(1, min(100, page_size))),
            "page": str(ocs_page),
            "sortmode": sort_mode if sort_mode in ("down", "new", "high", "alpha") else "down",
            "format": "json",
        }
        if search_query and search_query.strip():
            params["search"] = search_query.strip()

        query_string = urllib.parse.urlencode(params)
        url = f"{self.base_url}/content/data?{query_string}"

        req = self._build_request(url)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status_code = resp.getcode()
                raw_bytes = resp.read()
        except urllib.error.HTTPError as e:
            raise StoreResponseError(f"KDE Store HTTP Error {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise StoreNetworkError(f"Failed to connect to KDE Store ({e.reason})") from e
        except Exception as e:
            raise StoreNetworkError(f"Network error querying KDE Store: {e}") from e

        if status_code != 200:
            raise StoreResponseError(f"Unexpected response code from store: {status_code}")

        # Try parsing JSON first, then fall back to XML if provider returned XML
        text_content = raw_bytes.decode("utf-8", errors="replace")
        try:
            return self._parse_json_response(text_content, page, page_size)
        except json.JSONDecodeError:
            try:
                return self._parse_xml_response(text_content, page, page_size)
            except Exception as e:
                raise StoreResponseError(f"Could not parse KDE Store response payload: {e}") from e

    def _parse_json_response(self, text: str, page: int, page_size: int) -> CatalogQueryResult:
        """Parse OCS v1 JSON payload."""
        data = json.loads(text)
        if not isinstance(data, dict):
            raise StoreResponseError("Expected root JSON object from store.")

        status = data.get("status")
        if status not in ("ok", "success") and data.get("statuscode") not in (100, 200):
            msg = data.get("message", "Unknown error")
            raise StoreResponseError(f"KDE Store reported status error: {msg}")

        total_items = int(data.get("totalitems", 0))
        raw_items = data.get("data", [])
        if not isinstance(raw_items, list):
            raw_items = []

        entries: List[StoreThemeEntry] = []
        for raw in raw_items:
            if isinstance(raw, dict):
                entry = self._parse_theme_dict(raw)
                if entry:
                    entries.append(entry)

        has_more = (page * page_size) < total_items
        return CatalogQueryResult(
            items=entries,
            total_items=total_items,
            page=page,
            page_size=page_size,
            has_more=has_more,
        )

    def _parse_xml_response(self, text: str, page: int, page_size: int) -> CatalogQueryResult:
        """Parse OCS v1 XML payload as fallback."""
        root = ET.fromstring(text)
        meta = root.find("meta")
        total_items = 0
        if meta is not None:
            total_elem = meta.find("totalitems")
            if total_elem is not None and total_elem.text:
                try:
                    total_items = int(total_elem.text)
                except ValueError:
                    pass

        data_elem = root.find("data")
        entries: List[StoreThemeEntry] = []
        if data_elem is not None:
            for content in data_elem.findall("content"):
                item_dict: Dict[str, Any] = {}
                for child in content:
                    item_dict[child.tag] = child.text or ""
                entry = self._parse_theme_dict(item_dict)
                if entry:
                    entries.append(entry)

        if total_items == 0 and entries:
            total_items = len(entries)

        has_more = (page * page_size) < total_items
        return CatalogQueryResult(
            items=entries,
            total_items=total_items,
            page=page,
            page_size=page_size,
            has_more=has_more,
        )

    def _parse_theme_dict(self, d: Dict[str, Any]) -> Optional[StoreThemeEntry]:
        """Convert a raw dictionary of OCS fields into a clean StoreThemeEntry."""
        raw_id = str(d.get("id", "")).strip()
        name = str(d.get("name", "")).strip()
        if not raw_id or not name:
            return None

        version = str(d.get("version", "1.0")).strip()
        author = str(d.get("personid", "")).strip() or "KDE Community"
        summary = _strip_html(str(d.get("summary", "")))
        description = _strip_html(str(d.get("description", "")))
        if not summary and description:
            summary = description.split("\n")[0][:120]

        detail_url = str(d.get("detailpage", f"https://store.kde.org/p/{raw_id}")).strip()

        # Collect preview pictures
        previews: List[str] = []
        thumbnails: List[str] = []
        for i in range(1, 11):
            pic_key = f"previewpic{i}"
            thumb_key = f"smallpreviewpic{i}"
            pic = str(d.get(pic_key, "")).strip()
            thumb = str(d.get(thumb_key, "")).strip()
            if pic and pic.startswith("http"):
                previews.append(pic)
            if thumb and thumb.startswith("http"):
                thumbnails.append(thumb)

        primary_preview = previews[0] if previews else (thumbnails[0] if thumbnails else "")

        # Collect download links
        downloads: List[ThemeDownloadItem] = []
        for i in range(1, 15):
            link = str(d.get(f"downloadlink{i}", "")).strip()
            if not link or not link.startswith("http"):
                continue

            dl_name = str(d.get(f"downloadname{i}", f"theme_{raw_id}_{i}.tar.gz")).strip()
            size_raw = d.get(f"downloadsize{i}", 0)
            try:
                size_kb = int(size_raw)
            except (ValueError, TypeError):
                size_kb = 0

            md5 = str(d.get(f"downloadmd5sum{i}", "")).strip()
            ver = str(d.get(f"download_version{i}", version)).strip()

            downloads.append(
                ThemeDownloadItem(
                    index=i,
                    name=dl_name,
                    url=link,
                    size_kb=size_kb,
                    md5=md5,
                    version=ver,
                )
            )

        # Select primary download: prefer archives (.tar.gz, .tar.xz, .zip)
        primary_link = ""
        primary_name = ""
        primary_size = 0
        primary_md5 = ""
        if downloads:
            archive_items = [
                item for item in downloads
                if any(item.name.lower().endswith(ext) for ext in (".tar.gz", ".tar.xz", ".tgz", ".zip", ".tar.bz2"))
            ]
            chosen = archive_items[0] if archive_items else downloads[0]
            primary_link = chosen.url
            primary_name = chosen.name
            primary_size = chosen.size_kb
            primary_md5 = chosen.md5

        try:
            download_count = int(d.get("downloads", 0))
        except (ValueError, TypeError):
            download_count = 0

        try:
            score = int(d.get("score", 0))
        except (ValueError, TypeError):
            score = 0

        created = str(d.get("created", ""))
        updated = str(d.get("changed", ""))

        return StoreThemeEntry(
            id=raw_id,
            name=name,
            version=version,
            author=author,
            summary=summary,
            description=description,
            detail_url=detail_url,
            preview_url=primary_preview,
            preview_thumbnails=thumbnails,
            preview_images=previews,
            downloads=download_count,
            score=score,
            created_at=created,
            updated_at=updated,
            download_items=downloads,
            primary_download_url=primary_link,
            primary_download_name=primary_name,
            primary_download_size_kb=primary_size,
            primary_download_md5=primary_md5,
        )
