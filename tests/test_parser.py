"""Tests for the message parser module."""

from src.parser import ParsedMessage, parse_message


class TestParseMessage:
    """Test cases for the parse_message function."""

    def test_simple_quote_only(self):
        """Test parsing a simple quote without URL or tags."""
        result = parse_message("Be the change you wish to see")

        assert result.quote == "Be the change you wish to see"
        assert result.url is None
        assert result.tags == []

    def test_quote_with_url(self):
        """Test parsing a quote with a URL."""
        result = parse_message("Great article https://example.com/article")

        assert result.quote == "Great article"
        assert result.url == "https://example.com/article"
        assert result.tags == []

    def test_quote_with_tags(self):
        """Test parsing a quote with hashtags."""
        result = parse_message("Life is beautiful #wisdom #inspiration")

        assert result.quote == "Life is beautiful"
        assert result.url is None
        assert result.tags == ["wisdom", "inspiration"]

    def test_quote_with_url_and_tags(self):
        """Test parsing a quote with both URL and tags."""
        result = parse_message('"Be the change" https://example.com #wisdom #life')

        assert result.quote == "Be the change"
        assert result.url == "https://example.com"
        assert set(result.tags) == {"wisdom", "life"}

    def test_quoted_text_with_double_quotes(self):
        """Test that surrounding double quotes are removed."""
        result = parse_message('"This is a quoted text"')

        assert result.quote == "This is a quoted text"

    def test_quoted_text_with_single_quotes(self):
        """Test that surrounding single quotes are removed."""
        result = parse_message("'This is a quoted text'")

        assert result.quote == "This is a quoted text"

    def test_url_only(self):
        """Test parsing a message with only a URL."""
        result = parse_message("https://example.com/article")

        assert result.quote == ""
        assert result.url == "https://example.com/article"
        assert result.tags == []

    def test_http_url(self):
        """Test that HTTP URLs are also matched."""
        result = parse_message("Check this http://example.com")

        assert result.url == "http://example.com"

    def test_multiple_spaces_normalized(self):
        """Test that multiple spaces are collapsed to single spaces."""
        result = parse_message("This   has    multiple   spaces")

        assert result.quote == "This has multiple spaces"

    def test_whitespace_trimmed(self):
        """Test that leading/trailing whitespace is removed."""
        result = parse_message("   Whitespace around   ")

        assert result.quote == "Whitespace around"

    def test_complex_url_with_query_params(self):
        """Test parsing URLs with query parameters."""
        result = parse_message("Article https://example.com/page?id=123&ref=twitter #tech")

        assert result.quote == "Article"
        assert result.url == "https://example.com/page?id=123&ref=twitter"
        assert result.tags == ["tech"]

    def test_url_with_fragments(self):
        """Test parsing URLs with fragments."""
        result = parse_message("Section https://example.com/page#section-2")

        assert result.url == "https://example.com/page#section-2"

    def test_multiple_tags(self):
        """Test parsing multiple hashtags."""
        result = parse_message("Quote #tag1 #tag2 #tag3 #tag4")

        assert len(result.tags) == 4
        assert set(result.tags) == {"tag1", "tag2", "tag3", "tag4"}

    def test_tag_with_numbers(self):
        """Test that tags can contain numbers."""
        result = parse_message("Post #web3 #2024goals")

        assert "web3" in result.tags
        assert "2024goals" in result.tags

    def test_tag_with_underscores(self):
        """Test that tags can contain underscores."""
        result = parse_message("Note #my_tag #another_one")

        assert "my_tag" in result.tags
        assert "another_one" in result.tags

    def test_empty_string(self):
        """Test parsing an empty string."""
        result = parse_message("")

        assert result.quote == ""
        assert result.url is None
        assert result.tags == []

    def test_only_whitespace(self):
        """Test parsing whitespace-only string."""
        result = parse_message("   \n\t   ")

        assert result.quote == ""

    def test_returns_parsed_message_dataclass(self):
        """Test that the function returns a ParsedMessage instance."""
        result = parse_message("Test")

        assert isinstance(result, ParsedMessage)

    def test_url_in_middle_of_text(self):
        """Test parsing when URL is in the middle of text."""
        result = parse_message("Check https://example.com for more info")

        assert result.quote == "Check for more info"
        assert result.url == "https://example.com"

    def test_tags_scattered_in_text(self):
        """Test parsing when tags are scattered throughout."""
        result = parse_message("#start Some text #middle more text #end")

        assert "Some text more text" in result.quote
        assert set(result.tags) == {"start", "middle", "end"}
