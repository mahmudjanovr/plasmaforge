"""Unit tests for KDE Store / OCS v1 API catalog querying and metadata parsing."""

import json
from unittest.mock import MagicMock, patch
import urllib.error
import pytest

from plasmaforge.core.store_client import (
    DEFAULT_CATEGORY_ID,
    CatalogQueryResult,
    KdeStoreClient,
    StoreNetworkError,
    StoreResponseError,
    StoreThemeEntry,
    _strip_html,
)


SAMPLE_OCS_JSON = json.dumps({
    "status": "ok",
    "statuscode": 100,
    "message": "",
    "totalitems": 42,
    "itemsperpage": 2,
    "data": [
        {
            "id": 12345,
            "name": "Nordic KDE",
            "version": "2.1",
            "typeid": 722,
            "typename": "Global Themes (Plasma 6)",
            "personid": "alvatip",
            "created": "2026-01-10T12:00:00+00:00",
            "changed": "2026-02-15T16:30:00+00:00",
            "downloads": 85000,
            "score": 92,
            "summary": "Dark Nordic color theme for Plasma 6",
            "description": "<p>A dark and elegant <b>Nordic</b> theme.<br/>Includes color scheme and plasma style.</p>",
            "detailpage": "https://store.kde.org/p/12345",
            "previewpic1": "https://images.pling.com/preview1.png",
            "previewpic2": "https://images.pling.com/preview2.png",
            "smallpreviewpic1": "https://images.pling.com/thumb1.png",
            "downloadlink1": "https://files.pling.com/download/Nordic.tar.xz",
            "downloadname1": "Nordic-v2.1.tar.xz",
            "downloadsize1": "1048",
            "downloadmd5sum1": "0123456789abcdef0123456789abcdef",
            "download_version1": "2.1",
        },
        {
            "id": 67890,
            "name": "Sweet KDE",
            "version": "3.0",
            "typeid": 722,
            "typename": "Global Themes (Plasma 6)",
            "personid": "eliverlara",
            "created": "2026-03-01T10:00:00+00:00",
            "changed": "2026-03-05T11:00:00+00:00",
            "downloads": 120000,
            "score": 96,
            "summary": "Colorful modern dark theme",
            "description": "Sweet global theme with vibrant gradients.",
            "detailpage": "https://store.kde.org/p/67890",
            "previewpic1": "https://images.pling.com/sweet.png",
            "downloadlink1": "https://files.pling.com/download/Sweet.tar.gz",
            "downloadname1": "Sweet.tar.gz",
            "downloadsize1": "2048",
            "downloadmd5sum1": "abcdef0123456789abcdef0123456789",
        },
    ],
})

SAMPLE_OCS_XML = """<?xml version="1.0" encoding="utf-8"?>
<ocs>
  <meta>
    <status>ok</status>
    <statuscode>100</statuscode>
    <totalitems>1</totalitems>
    <itemsperpage>10</itemsperpage>
  </meta>
  <data>
    <content details="summary">
      <id>99999</id>
      <name>Breeze Twilight Extra</name>
      <version>1.5</version>
      <typeid>722</typeid>
      <personid>kdecommunity</personid>
      <summary>Twilight look for Plasma 6</summary>
      <description>&lt;p&gt;Hybrid theme with dark panels and light apps.&lt;/p&gt;</description>
      <detailpage>https://store.kde.org/p/99999</detailpage>
      <previewpic1>https://images.pling.com/twilight.png</previewpic1>
      <downloadlink1>https://files.pling.com/download/twilight.tar.gz</downloadlink1>
      <downloadname1>twilight.tar.gz</downloadname1>
      <downloadsize1>512</downloadsize1>
      <downloadmd5sum1>feedfacefeedfacefeedfacefeedface</downloadmd5sum1>
    </content>
  </data>
</ocs>
"""


def test_html_cleaner() -> None:
    """Verify HTML stripping and whitespace handling."""
    raw = "<p>First paragraph.</p><br/><p>Second line with <a href='https://kde.org'>link</a> &amp; entities.</p>"
    cleaned = _strip_html(raw)
    assert "<" not in cleaned
    assert "First paragraph." in cleaned
    assert "Second line with link & entities." in cleaned


def test_parse_json_catalog_success() -> None:
    """Verify parsing valid OCS v1 JSON response into typed dataclasses."""
    client = KdeStoreClient()
    result: CatalogQueryResult = client._parse_json_response(SAMPLE_OCS_JSON, page=1, page_size=2)

    assert result.total_items == 42
    assert result.page == 1
    assert result.page_size == 2
    assert result.has_more is True
    assert len(result.items) == 2

    nordic = result.items[0]
    assert nordic.id == "12345"
    assert nordic.name == "Nordic KDE"
    assert nordic.version == "2.1"
    assert nordic.author == "alvatip"
    assert nordic.downloads == 85000
    assert nordic.score == 92
    assert nordic.primary_download_name == "Nordic-v2.1.tar.xz"
    assert nordic.primary_download_size_kb == 1048
    assert nordic.primary_download_md5 == "0123456789abcdef0123456789abcdef"
    assert len(nordic.preview_images) == 2
    assert nordic.preview_thumbnails == ["https://images.pling.com/thumb1.png"]
    assert "A dark and elegant Nordic theme." in nordic.description

    sweet = result.items[1]
    assert sweet.id == "67890"
    assert sweet.name == "Sweet KDE"
    assert sweet.downloads == 120000
    assert sweet.primary_download_url == "https://files.pling.com/download/Sweet.tar.gz"


def test_parse_xml_catalog_fallback() -> None:
    """Verify XML fallback parsing if store returns XML content."""
    client = KdeStoreClient()
    result: CatalogQueryResult = client._parse_xml_response(SAMPLE_OCS_XML, page=1, page_size=10)

    assert result.total_items == 1
    assert len(result.items) == 1
    theme = result.items[0]
    assert theme.id == "99999"
    assert theme.name == "Breeze Twilight Extra"
    assert theme.author == "kdecommunity"
    assert theme.primary_download_name == "twilight.tar.gz"
    assert theme.primary_download_md5 == "feedfacefeedfacefeedfacefeedface"
    assert "Hybrid theme with dark panels and light apps." in theme.description


def test_query_parameters_constructed_correctly() -> None:
    """Verify URL generation with category, page, pagesize, search, and sort."""
    client = KdeStoreClient(base_url="https://mock.store/ocs/v1", category_id=722)

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_resp.read.return_value = SAMPLE_OCS_JSON.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client.fetch_catalog(
            search_query="Nordic",
            page=2,
            page_size=20,
            sort_mode="new",
        )

        assert mock_urlopen.called
        req = mock_urlopen.call_args[0][0]
        url = req.full_url
        assert "categories=722" in url
        assert "search=Nordic" in url
        assert "pagesize=20" in url
        assert "page=1" in url  # 0-indexed page for page 2
        assert "sortmode=new" in url
        assert "format=json" in url


def test_network_error_raises_store_network_error() -> None:
    """Verify URLError / connection timeout triggers StoreNetworkError."""
    client = KdeStoreClient()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection timed out")):
        with pytest.raises(StoreNetworkError) as exc_info:
            client.fetch_catalog()
        assert "Failed to connect to KDE Store" in str(exc_info.value)


def test_http_error_raises_store_response_error() -> None:
    """Verify HTTP 500/404 errors trigger StoreResponseError."""
    client = KdeStoreClient()
    http_err = urllib.error.HTTPError(
        url="https://api.kde-look.org/ocs/v1/content/data",
        code=502,
        msg="Bad Gateway",
        hdrs=MagicMock(),
        fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=http_err):
        with pytest.raises(StoreResponseError) as exc_info:
            client.fetch_catalog()
        assert "HTTP Error 502" in str(exc_info.value)


def test_store_error_payload_handling() -> None:
    """Verify honest error reporting when store returns non-ok status in JSON."""
    client = KdeStoreClient()
    error_json = json.dumps({
        "status": "failed",
        "statuscode": 101,
        "message": "Invalid category ID specified.",
    })
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_resp.read.return_value = error_json.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        with pytest.raises(StoreResponseError) as exc_info:
            client.fetch_catalog()
        assert "Invalid category ID specified." in str(exc_info.value)
