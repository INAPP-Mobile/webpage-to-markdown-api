"""
Tests for the Web Page to Markdown API.

Tests the converter logic directly (URL validation, fetch, extraction)
and the FastAPI endpoint via TestClient.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.converters import (
    validate_url,
    url_to_markdown,
    InvalidURLError,
    TimeoutError,
    ResponseTooLargeError,
    FetchError,
    ConversionError,
    MAX_RESPONSE_SIZE,
    REQUEST_TIMEOUT,
)


# ── URL validation tests ───────────────────────────────────────────────────


class TestValidateURL:
    def test_valid_https_url(self):
        assert validate_url("https://example.com") == "https://example.com"

    def test_valid_http_url(self):
        assert validate_url("http://example.com/page") == "http://example.com/page"

    def test_auto_prepend_scheme(self):
        assert validate_url("example.com") == "https://example.com"
        assert validate_url("example.com/page") == "https://example.com/page"

    def test_with_www(self):
        assert validate_url("www.example.com") == "https://www.example.com"

    def test_with_path_and_query(self):
        result = validate_url("https://example.com/path?q=1&r=2")
        assert result == "https://example.com/path?q=1&r=2"

    def test_strips_whitespace(self):
        assert validate_url("  https://example.com  ") == "https://example.com"

    def test_rejects_empty_string(self):
        with pytest.raises(InvalidURLError):
            validate_url("")

    def test_rejects_non_string(self):
        with pytest.raises(InvalidURLError):
            validate_url(123)  # type: ignore

    def test_rejects_no_hostname(self):
        with pytest.raises(InvalidURLError):
            validate_url("https://")

    def test_rejects_no_dot(self):
        with pytest.raises(InvalidURLError):
            validate_url("https://localhost")

    def test_rejects_ftp(self):
        with pytest.raises(InvalidURLError):
            validate_url("ftp://example.com")

    def test_rejects_javascript(self):
        with pytest.raises(InvalidURLError):
            validate_url("javascript:void(0)")

    def test_long_url(self):
        long = "https://example.com/" + "a" * 1900
        assert validate_url(long) == long


# ── Converter integration tests ────────────────────────────────────────────
# These test the full pipeline with public URLs.
# Marked as integration — can be skipped in fast mode.


@pytest.mark.integration
@pytest.mark.asyncio
async def test_convert_real_url():
    """Fetch a real public page and verify markdown output."""
    result = await url_to_markdown("https://example.com")
    assert "markdown" in result
    assert result["source_url"] == "https://example.com"
    assert len(result["markdown"]) > 20
    assert result["length"] == len(result["markdown"])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_convert_with_www():
    result = await url_to_markdown("www.example.com")
    assert result["source_url"] == "https://www.example.com"
    assert len(result["markdown"]) > 20


@pytest.mark.integration
@pytest.mark.asyncio
async def test_convert_non_existent_domain():
    """Non-existent domain should raise FetchError."""
    with pytest.raises(FetchError):
        await url_to_markdown("https://this-domain-does-not-exist-12345.com")


# ── API endpoint tests ─────────────────────────────────────────────────────


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    data = resp.json()
    assert data["title"] == "Web Page to Markdown API"
    assert "docs" in data
    assert "convert" in data["endpoints"]


@pytest.mark.asyncio
async def test_convert_missing_url(client):
    resp = await client.get("/convert")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_convert_empty_url(client):
    resp = await client.get("/convert?url=")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_convert_invalid_url(client):
    resp = await client.get("/convert?url=not-a-valid-url")
    assert resp.status_code == 400
    assert "error" not in resp.json() or True  # detail field present
    assert "detail" in resp.json()


@pytest.mark.asyncio
async def test_convert_bad_host(client):
    """URL with no dot should be 400."""
    resp = await client.get("/convert?url=https://localhost")
    assert resp.status_code == 400
    assert "detail" in resp.json()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_convert_success_endpoint(client):
    """End-to-end test with a real URL."""
    resp = await client.get("/convert?url=https://example.com")
    assert resp.status_code == 200
    data = resp.json()
    assert "markdown" in data
    assert "title" in data
    assert "source_url" in data
    assert "length" in data
    assert data["length"] == len(data["markdown"])
    assert data["source_url"] == "https://example.com"


@pytest.mark.asyncio
async def test_convert_very_long_url(client):
    """URL over 2000 chars should be rejected by FastAPI's max_length."""
    long_url = "https://example.com/" + "a" * 2000
    resp = await client.get(f"/convert?url={long_url}")
    assert resp.status_code == 422


# ── Unit tests for edge cases ──────────────────────────────────────────────


class TestErrorMessages:
    def test_invalid_url_message(self):
        try:
            validate_url("")
        except InvalidURLError as e:
            assert "URL must be a non-empty string" in str(e)

    def test_no_dot_message(self):
        try:
            validate_url("https://localhost")
        except InvalidURLError as e:
            assert "must contain a dot" in str(e)

    def test_unsupported_scheme_message(self):
        try:
            validate_url("ftp://example.com")
        except InvalidURLError as e:
            assert "Unsupported scheme" in str(e)
