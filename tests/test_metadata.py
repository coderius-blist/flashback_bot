"""Tests for the metadata extraction module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from src.metadata import (
    ArticleMetadata,
    _extract_author,
    _extract_title,
    fetch_metadata,
)


class TestExtractTitle:
    """Test cases for the _extract_title helper function."""

    def test_extracts_og_title(self):
        """Test extraction of og:title meta tag."""
        html = '<html><head><meta property="og:title" content="OG Title" /></head></html>'
        soup = BeautifulSoup(html, "html.parser")

        assert _extract_title(soup) == "OG Title"

    def test_falls_back_to_title_tag(self):
        """Test fallback to <title> tag when og:title is missing."""
        html = "<html><head><title>Page Title</title></head></html>"
        soup = BeautifulSoup(html, "html.parser")

        assert _extract_title(soup) == "Page Title"

    def test_prefers_og_title_over_title_tag(self):
        """Test that og:title takes precedence over <title>."""
        html = '''
        <html><head>
            <title>Title Tag</title>
            <meta property="og:title" content="OG Title" />
        </head></html>
        '''
        soup = BeautifulSoup(html, "html.parser")

        assert _extract_title(soup) == "OG Title"

    def test_returns_none_when_no_title(self):
        """Test that None is returned when no title is found."""
        html = "<html><head></head><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")

        assert _extract_title(soup) is None

    def test_strips_whitespace_from_title(self):
        """Test that whitespace is stripped from titles."""
        html = '<html><head><meta property="og:title" content="  Spaced Title  " /></head></html>'
        soup = BeautifulSoup(html, "html.parser")

        assert _extract_title(soup) == "Spaced Title"

    def test_handles_empty_og_title(self):
        """Test handling of empty og:title content."""
        html = '<html><head><meta property="og:title" content="" /><title>Fallback</title></head></html>'
        soup = BeautifulSoup(html, "html.parser")

        # Empty content should fall through to title tag
        assert _extract_title(soup) == "Fallback"


class TestExtractAuthor:
    """Test cases for the _extract_author helper function."""

    def test_extracts_meta_author(self):
        """Test extraction from meta name='author' tag."""
        html = '<html><head><meta name="author" content="John Doe" /></head></html>'
        soup = BeautifulSoup(html, "html.parser")

        assert _extract_author(soup) == "John Doe"

    def test_extracts_article_author(self):
        """Test extraction from article:author meta tag."""
        html = '<html><head><meta property="article:author" content="Jane Smith" /></head></html>'
        soup = BeautifulSoup(html, "html.parser")

        assert _extract_author(soup) == "Jane Smith"

    def test_extracts_twitter_creator(self):
        """Test extraction from twitter:creator meta tag."""
        html = '<html><head><meta name="twitter:creator" content="@johndoe" /></head></html>'
        soup = BeautifulSoup(html, "html.parser")

        assert _extract_author(soup) == "@johndoe"

    def test_extracts_from_author_class(self):
        """Test extraction from element with 'author' class."""
        html = '<html><body><span class="author">Bob Wilson</span></body></html>'
        soup = BeautifulSoup(html, "html.parser")

        assert _extract_author(soup) == "Bob Wilson"

    def test_extracts_from_byline_class(self):
        """Test extraction from element with 'byline' class."""
        html = '<html><body><div class="byline">Alice Johnson</div></body></html>'
        soup = BeautifulSoup(html, "html.parser")

        assert _extract_author(soup) == "Alice Johnson"

    def test_strips_by_prefix(self):
        """Test that 'By ' prefix is stripped from author names."""
        html = '<html><body><span class="author">By John Doe</span></body></html>'
        soup = BeautifulSoup(html, "html.parser")

        assert _extract_author(soup) == "John Doe"

    def test_strips_written_by_prefix(self):
        """Test that 'Written by ' prefix is stripped."""
        html = '<html><body><span class="author">Written by Jane Doe</span></body></html>'
        soup = BeautifulSoup(html, "html.parser")

        assert _extract_author(soup) == "Jane Doe"

    def test_returns_none_when_no_author(self):
        """Test that None is returned when no author is found."""
        html = "<html><head></head><body><p>No author here</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")

        assert _extract_author(soup) is None

    def test_prefers_meta_over_class(self):
        """Test that meta tags take precedence over class-based extraction."""
        html = '''
        <html>
        <head><meta name="author" content="Meta Author" /></head>
        <body><span class="author">Class Author</span></body>
        </html>
        '''
        soup = BeautifulSoup(html, "html.parser")

        assert _extract_author(soup) == "Meta Author"


class TestFetchMetadata:
    """Test cases for the fetch_metadata function."""

    @pytest.mark.asyncio
    async def test_extracts_domain_from_url(self):
        """Test that domain is correctly extracted from URL."""
        with patch("src.metadata.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = "<html><head><title>Test</title></head></html>"
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_metadata("https://www.example.com/article")

            assert result.domain == "example.com"

    @pytest.mark.asyncio
    async def test_removes_www_from_domain(self):
        """Test that 'www.' is stripped from domain."""
        with patch("src.metadata.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = "<html><head><title>Test</title></head></html>"
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_metadata("https://www.test-site.org/page")

            assert result.domain == "test-site.org"

    @pytest.mark.asyncio
    async def test_returns_metadata_on_success(self, mock_html_response):
        """Test successful metadata extraction."""
        with patch("src.metadata.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = mock_html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_metadata("https://example.com/article")

            assert isinstance(result, ArticleMetadata)
            assert result.title == "Test Article"
            assert result.author == "John Doe"
            assert result.domain == "example.com"

    @pytest.mark.asyncio
    async def test_handles_network_error(self):
        """Test that network errors return partial metadata with domain only."""
        import httpx

        with patch("src.metadata.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_metadata("https://example.com/article")

            assert result.domain == "example.com"
            assert result.title is None
            assert result.author is None

    @pytest.mark.asyncio
    async def test_handles_timeout(self):
        """Test that timeouts return partial metadata with domain only."""
        import httpx

        with patch("src.metadata.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_metadata("https://slow-site.com/page")

            assert result.domain == "slow-site.com"
            assert result.title is None
            assert result.author is None

    @pytest.mark.asyncio
    async def test_handles_http_error(self):
        """Test that HTTP errors (404, 500) return partial metadata."""
        import httpx

        with patch("src.metadata.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock())
            )

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_metadata("https://example.com/not-found")

            assert result.domain == "example.com"
            assert result.title is None

    @pytest.mark.asyncio
    async def test_returns_article_metadata_dataclass(self):
        """Test that the function returns an ArticleMetadata instance."""
        with patch("src.metadata.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = "<html><head><title>Test</title></head></html>"
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_metadata("https://example.com")

            assert isinstance(result, ArticleMetadata)
