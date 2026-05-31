"""
Web page to clean Markdown converter.

Fetches a URL via httpx, extracts readable content using
readability-lxml (Python port of Mozilla's Readability),
and converts the cleaned HTML to Markdown via markdownify.
"""

import re
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from readability import Document

# ── Constants ──────────────────────────────────────────────────────────────

MAX_RESPONSE_SIZE = 1_000_000  # 1 MB
REQUEST_TIMEOUT = 10.0  # seconds
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# ── Exceptions ─────────────────────────────────────────────────────────────


class ConversionError(Exception):
    """Base exception for conversion failures."""


class InvalidURLError(ConversionError):
    """Raised when the provided URL is invalid."""


class TimeoutError(ConversionError):
    """Raised when the request times out."""


class ResponseTooLargeError(ConversionError):
    """Raised when the response exceeds the size limit."""


class FetchError(ConversionError):
    """Raised when the URL cannot be fetched (non-2xx, DNS, etc.)."""


class ExtractionError(ConversionError):
    """Raised when readable content cannot be extracted."""


# ── URL validation ─────────────────────────────────────────────────────────


def validate_url(url: str) -> str:
    """Validate and normalise a URL. Returns the normalised URL on success."""
    if not url or not isinstance(url, str):
        raise InvalidURLError("URL must be a non-empty string.")

    url = url.strip()

    # Reject known non-HTTP schemes before any normalisation
    if "://" in url:
        scheme = url.split("://", 1)[0].lower()
        if scheme not in ("http", "https"):
            raise InvalidURLError(
                f"Unsupported scheme '{scheme}'. Only http/https allowed."
            )

    # Auto-prepend scheme if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    if not parsed.netloc:
        raise InvalidURLError(
            f"Invalid URL: '{url}' — no hostname detected."
        )

    # Basic domain sanity (must contain at least one dot)
    if "." not in parsed.netloc:
        raise InvalidURLError(
            f"Invalid domain: '{parsed.netloc}' — must contain a dot."
        )

    return url


# ── HTTP fetching ──────────────────────────────────────────────────────────


async def fetch_page(url: str) -> str:
    """
    Fetch a web page and return its HTML body.

    Raises InvalidURLError, TimeoutError, ResponseTooLargeError, FetchError.
    """
    validate_url(url)

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            response = await client.get(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": (
                        "text/html,application/xhtml+xml,"
                        "application/xml;q=0.9,*/*;q=0.8"
                    ),
                    "Accept-Language": "en-US,en;q=0.5",
                },
                follow_redirects=True,
            )
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Request timed out after {REQUEST_TIMEOUT}s for: {url}"
            )
        except httpx.RequestError as exc:
            raise FetchError(
                f"Failed to fetch URL: {exc}"
            )

    if response.status_code != 200:
        raise FetchError(
            f"HTTP {response.status_code} for: {url}"
        )

    # Check Content-Length header first (fast path)
    content_length = response.headers.get("content-length")
    if content_length and int(content_length) > MAX_RESPONSE_SIZE:
        raise ResponseTooLargeError(
            f"Response too large: {content_length} bytes "
            f"(max {MAX_RESPONSE_SIZE} bytes)."
        )

    # Check actual body size
    if len(response.content) > MAX_RESPONSE_SIZE:
        raise ResponseTooLargeError(
            f"Response too large: {len(response.content)} bytes "
            f"(max {MAX_RESPONSE_SIZE} bytes)."
        )

    return response.text


# ── Content extraction ─────────────────────────────────────────────────────


def extract_readable_content(html: str, source_url: str) -> str:
    """
    Extract the readable (article) HTML from a full web page using
    readability-lxml. Falls back to <body> content if readability fails.

    Returns cleaned HTML string.
    """
    doc = Document(html)
    summary_html = doc.summary()

    if not summary_html or len(summary_html.strip()) < 50:
        # Fallback: try to extract <body> content
        soup = BeautifulSoup(html, "html.parser")
        body = soup.find("body")
        if body:
            summary_html = str(body)
        else:
            raise ExtractionError(
                "Could not extract readable content from the page."
            )

    return summary_html


def convert_to_markdown(html: str, title: Optional[str] = None) -> str:
    """
    Convert cleaned HTML to Markdown.

    Prepends the page title as an H1 heading when available.
    """
    import markdownify

    md = markdownify.markdownify(
        html,
        heading_style="ATX",  # Use # style headings
        bullets="-",
        strip=["script", "style", "nav", "footer", "aside"],
    )

    # Clean up excessive whitespace
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = md.strip()

    if title:
        md = f"# {title}\n\n{md}"

    return md


# ── High-level API ─────────────────────────────────────────────────────────


async def url_to_markdown(url: str) -> dict:
    """
    Fetch a web page and return clean markdown.

    Returns a dict with:
      - title: page title (or None)
      - markdown: clean markdown content
      - source_url: the original/normalised URL
      - length: character count of the markdown

    Raises ConversionError (or subclasses) on failure.
    """
    url = validate_url(url)
    html = await fetch_page(url)

    # Extract title via readability
    doc = Document(html)
    title = doc.title()

    summary_html = extract_readable_content(html, url)
    markdown = convert_to_markdown(summary_html, title=title)

    return {
        "title": title,
        "markdown": markdown,
        "source_url": url,
        "length": len(markdown),
    }
