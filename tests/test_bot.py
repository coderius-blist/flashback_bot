"""Tests for the bot module."""

from datetime import datetime, timedelta

from src.bot import format_quote, format_relative_time


class TestFormatRelativeTime:
    """Test cases for the format_relative_time function."""

    def test_just_now(self):
        """Test formatting for timestamps less than a minute ago."""
        now = datetime.now()
        timestamp = now.isoformat()
        result = format_relative_time(timestamp)
        assert result == "just now"

    def test_minutes_ago(self):
        """Test formatting for timestamps in minutes."""
        timestamp = (datetime.now() - timedelta(minutes=30)).isoformat()
        result = format_relative_time(timestamp)
        assert result == "30m ago"

    def test_hours_ago(self):
        """Test formatting for timestamps in hours."""
        timestamp = (datetime.now() - timedelta(hours=5)).isoformat()
        result = format_relative_time(timestamp)
        assert result == "5h ago"

    def test_yesterday(self):
        """Test formatting for yesterday."""
        timestamp = (datetime.now() - timedelta(days=1)).isoformat()
        result = format_relative_time(timestamp)
        assert result == "yesterday"

    def test_days_ago(self):
        """Test formatting for timestamps in days."""
        timestamp = (datetime.now() - timedelta(days=4)).isoformat()
        result = format_relative_time(timestamp)
        assert result == "4d ago"

    def test_weeks_ago(self):
        """Test formatting for timestamps in weeks."""
        timestamp = (datetime.now() - timedelta(weeks=3)).isoformat()
        result = format_relative_time(timestamp)
        assert result == "3w ago"

    def test_months_ago(self):
        """Test formatting for timestamps in months."""
        timestamp = (datetime.now() - timedelta(days=90)).isoformat()
        result = format_relative_time(timestamp)
        assert result == "3mo ago"

    def test_years_ago(self):
        """Test formatting for timestamps in years."""
        timestamp = (datetime.now() - timedelta(days=730)).isoformat()
        result = format_relative_time(timestamp)
        assert result == "2y ago"

    def test_invalid_timestamp(self):
        """Test that invalid timestamps return empty string."""
        result = format_relative_time("invalid")
        assert result == ""

    def test_none_timestamp(self):
        """Test that None returns empty string."""
        result = format_relative_time(None)
        assert result == ""


class TestFormatQuote:
    """Test cases for the format_quote function."""

    def test_simple_quote(self):
        """Test formatting a simple quote."""
        quote = {"id": 1, "text": "Be the change"}
        result = format_quote(quote)
        assert '"Be the change"' in result

    def test_quote_with_id(self):
        """Test formatting with show_id=True."""
        quote = {"id": 42, "text": "Test quote"}
        result = format_quote(quote, show_id=True)
        assert "[#42]" in result

    def test_quote_with_favorite(self):
        """Test formatting a favorite quote."""
        quote = {"id": 1, "text": "Favorite quote", "is_favorite": 1}
        result = format_quote(quote)
        assert "⭐" in result

    def test_quote_with_source_title(self):
        """Test formatting with source title."""
        quote = {
            "id": 1,
            "text": "Quote",
            "source_title": "Great Article"
        }
        result = format_quote(quote)
        assert "Great Article" in result

    def test_quote_with_author(self):
        """Test formatting with author."""
        quote = {
            "id": 1,
            "text": "Quote",
            "source_title": "Article",
            "source_author": "John Doe"
        }
        result = format_quote(quote)
        assert "by John Doe" in result

    def test_quote_with_domain(self):
        """Test formatting with domain when no author."""
        quote = {
            "id": 1,
            "text": "Quote",
            "source_domain": "example.com"
        }
        result = format_quote(quote)
        assert "(example.com)" in result

    def test_quote_with_url(self):
        """Test formatting with URL."""
        quote = {
            "id": 1,
            "text": "Quote",
            "url": "https://example.com"
        }
        result = format_quote(quote)
        assert "https://example.com" in result

    def test_quote_with_tags(self):
        """Test formatting with tags."""
        quote = {
            "id": 1,
            "text": "Quote",
            "tags": "wisdom,inspiration"
        }
        result = format_quote(quote)
        assert "#wisdom" in result
        assert "#inspiration" in result

    def test_quote_with_timestamp(self):
        """Test formatting with timestamp."""
        timestamp = (datetime.now() - timedelta(days=2)).isoformat()
        quote = {
            "id": 1,
            "text": "Quote",
            "created_at": timestamp
        }
        result = format_quote(quote)
        assert "📅 Saved" in result
        assert "2d ago" in result

    def test_quote_with_all_fields(self):
        """Test formatting with all fields populated."""
        timestamp = (datetime.now() - timedelta(hours=5)).isoformat()
        quote = {
            "id": 123,
            "text": "Complete quote",
            "url": "https://example.com/article",
            "source_title": "Amazing Article",
            "source_author": "Jane Smith",
            "source_domain": "example.com",
            "tags": "philosophy,wisdom",
            "is_favorite": 1,
            "created_at": timestamp
        }
        result = format_quote(quote, show_id=True)

        assert "[#123]" in result
        assert '"Complete quote"' in result
        assert "⭐" in result
        assert "Amazing Article" in result
        assert "by Jane Smith" in result
        assert "https://example.com/article" in result
        assert "#philosophy" in result
        assert "#wisdom" in result
        assert "📅 Saved" in result
        assert "5h ago" in result
