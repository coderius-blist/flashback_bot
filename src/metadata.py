import asyncio
import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# URL validation pattern
URL_PATTERN = re.compile(
    r'^https?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
    r'localhost|'  # localhost
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

# Maximum URL length to prevent abuse
MAX_URL_LENGTH = 2048

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 0.5  # seconds


@dataclass
class ArticleMetadata:
    title: str | None
    author: str | None
    domain: str


def is_valid_url(url: str) -> bool:
    """Validate URL format and length."""
    if not url or len(url) > MAX_URL_LENGTH:
        return False
    return bool(URL_PATTERN.match(url))


async def fetch_metadata(url: str, retries: int = MAX_RETRIES) -> ArticleMetadata:
    """
    Fetch article metadata from a URL.

    Extracts title, author, and domain from the page.
    Includes URL validation, specific error handling, and retry logic.

    Args:
        url: The URL to fetch metadata from
        retries: Number of retry attempts for transient failures

    Returns:
        ArticleMetadata with extracted information, or partial data on failure
    """
    # Extract domain early - we'll need it even if fetch fails
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "") or "unknown"
    except Exception:
        domain = "unknown"

    # Validate URL format
    if not is_valid_url(url):
        logger.warning(f"Invalid URL format: {url[:100]}...")
        return ArticleMetadata(title=None, author=None, domain=domain)

    last_exception = None
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=httpx.Timeout(10.0, connect=5.0)
            ) as client:
                response = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ReadWiser/1.0)"
                })
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            title = _extract_title(soup)
            author = _extract_author(soup)

            logger.debug(f"Successfully fetched metadata from {domain}: title='{title}', author='{author}'")
            return ArticleMetadata(title=title, author=author, domain=domain)

        except httpx.TimeoutException as e:
            last_exception = e
            logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{retries})")
            if attempt < retries - 1:
                await asyncio.sleep(INITIAL_BACKOFF * (2 ** attempt))
            continue

        except httpx.ConnectError as e:
            last_exception = e
            logger.warning(f"Connection error for {url}: {e}")
            # Don't retry connection errors - they're likely persistent
            break

        except httpx.HTTPStatusError as e:
            last_exception = e
            status_code = e.response.status_code
            logger.warning(f"HTTP {status_code} error for {url}")
            # Don't retry client errors (4xx), only server errors (5xx)
            if 400 <= status_code < 500:
                break
            if attempt < retries - 1:
                await asyncio.sleep(INITIAL_BACKOFF * (2 ** attempt))
            continue

        except httpx.RequestError as e:
            last_exception = e
            logger.warning(f"Request error for {url}: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(INITIAL_BACKOFF * (2 ** attempt))
            continue

        except Exception as e:
            last_exception = e
            logger.error(f"Unexpected error fetching {url}: {type(e).__name__}: {e}")
            break

    logger.info(f"Failed to fetch metadata from {url} after {retries} attempts: {last_exception}")
    return ArticleMetadata(title=None, author=None, domain=domain)


def _extract_title(soup: BeautifulSoup) -> str | None:
    """Extract page title from HTML soup."""
    # Try og:title first (usually cleaner)
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"].strip()

    # Fall back to <title> tag
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        return title_tag.string.strip()

    return None


def _extract_author(soup: BeautifulSoup) -> str | None:
    """Extract author information from HTML soup."""
    # Try various meta tags
    author_selectors = [
        ("meta", {"name": "author"}),
        ("meta", {"property": "article:author"}),
        ("meta", {"property": "og:article:author"}),
        ("meta", {"name": "twitter:creator"}),
    ]

    for tag, attrs in author_selectors:
        element = soup.find(tag, attrs)
        if element and element.get("content"):
            return element["content"].strip()

    # Try common author elements
    author_classes = ["author", "byline", "author-name", "post-author"]
    for cls in author_classes:
        element = soup.find(class_=cls)
        if element and element.get_text(strip=True):
            text = element.get_text(strip=True)
            # Clean up common prefixes
            for prefix in ["By ", "by ", "Written by ", "Author: "]:
                if text.startswith(prefix):
                    text = text[len(prefix):]
            return text

    return None
