"""Shared pytest fixtures for ReadWiser tests."""

import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Store original DATABASE_PATH to restore later
_original_db_path = None
_original_data_dir = None


@pytest_asyncio.fixture
async def test_db(tmp_path, monkeypatch):
    """Create and initialize an isolated test database."""
    test_db_path = tmp_path / "test_quotes.db"
    test_data_dir = tmp_path

    # Import modules
    import config
    from src import database

    # Monkeypatch at module level - this persists for the test function
    monkeypatch.setattr(config, "DATABASE_PATH", test_db_path)
    monkeypatch.setattr(config, "DATA_DIR", test_data_dir)
    monkeypatch.setattr(database, "DATABASE_PATH", test_db_path)
    monkeypatch.setattr(database, "DATA_DIR", test_data_dir)

    # Initialize the database
    await database.init_db()

    yield test_db_path


@pytest.fixture
def sample_quotes():
    """Provide sample quote data for testing."""
    return [
        {
            "text": "Be the change you wish to see in the world",
            "url": "https://example.com/gandhi",
            "tags": ["wisdom", "inspiration"],
        },
        {
            "text": "The only thing we have to fear is fear itself",
            "url": "https://history.com/fdr",
            "tags": ["courage", "politics"],
        },
        {
            "text": "To be or not to be, that is the question",
            "url": None,
            "tags": ["shakespeare", "philosophy"],
        },
    ]


@pytest.fixture
def mock_html_response():
    """Provide mock HTML content for metadata extraction tests."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Article - Example Site</title>
        <meta property="og:title" content="Test Article" />
        <meta name="author" content="John Doe" />
        <meta property="article:author" content="John Doe" />
    </head>
    <body>
        <h1>Test Article</h1>
        <p class="author">By John Doe</p>
        <p>Article content here...</p>
    </body>
    </html>
    """


@pytest.fixture
def mock_html_minimal():
    """Provide minimal HTML without metadata."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simple Page</title>
    </head>
    <body>
        <p>Content</p>
    </body>
    </html>
    """
