import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps
from typing import ParamSpec, TypeVar

import aiosqlite

from config import DATABASE_PATH, DATA_DIR

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass


def handle_db_errors(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to handle database errors with logging."""
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except aiosqlite.Error as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            raise DatabaseError(f"Database operation failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {type(e).__name__}: {e}")
            raise
    return wrapper


async def _get_connection():
    """Get a database connection with foreign keys enabled."""
    db = await aiosqlite.connect(DATABASE_PATH)
    await db.execute("PRAGMA foreign_keys = ON")
    return db


@handle_db_errors
async def init_db():
    """Initialize the database with required tables."""
    try:
        DATA_DIR.mkdir(exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create data directory {DATA_DIR}: {e}")
        raise DatabaseError(f"Cannot create data directory: {e}") from e

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")

        # Users table - tracks all users for sending digests
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                chat_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                digest_enabled INTEGER DEFAULT 1,
                daily_quote_enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Quotes table - now with user_id
        await db.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                url TEXT,
                source_title TEXT,
                source_author TEXT,
                source_domain TEXT,
                tags TEXT,
                is_favorite INTEGER DEFAULT 0,
                times_shown INTEGER DEFAULT 0,
                last_shown TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (chat_id)
            )
        """)

        # Create indexes for common queries
        await db.execute("CREATE INDEX IF NOT EXISTS idx_quotes_user_id ON quotes(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_quotes_created_at ON quotes(created_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_chat_id ON users(chat_id)")

        await db.commit()
        logger.info("Database initialized successfully")

        # Migration: add new columns to existing databases
        await _migrate_db(db)


async def _migrate_db(db):
    """Add new columns if they don't exist (for existing databases)."""
    cursor = await db.execute("PRAGMA table_info(quotes)")
    columns = {row[1] for row in await cursor.fetchall()}

    migrations = [
        ("is_favorite", "INTEGER DEFAULT 0"),
        ("times_shown", "INTEGER DEFAULT 0"),
        ("last_shown", "TIMESTAMP"),
        ("user_id", "INTEGER DEFAULT 0"),
    ]

    for col_name, col_type in migrations:
        if col_name not in columns:
            logger.info(f"Migrating database: adding column {col_name}")
            await db.execute(f"ALTER TABLE quotes ADD COLUMN {col_name} {col_type}")

    await db.commit()


# ============ User functions ============

@handle_db_errors
async def register_user(chat_id: int, username: str = None, first_name: str = None) -> bool:
    """Register a new user or update existing. Returns True if new user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute("SELECT chat_id FROM users WHERE chat_id = ?", (chat_id,))
        exists = await cursor.fetchone()

        if exists:
            await db.execute(
                "UPDATE users SET username = ?, first_name = ? WHERE chat_id = ?",
                (username, first_name, chat_id)
            )
            await db.commit()
            logger.debug(f"Updated user {chat_id}")
            return False
        else:
            await db.execute(
                "INSERT INTO users (chat_id, username, first_name) VALUES (?, ?, ?)",
                (chat_id, username, first_name)
            )
            await db.commit()
            logger.info(f"Registered new user {chat_id} ({username})")
            return True


@handle_db_errors
async def get_all_users() -> list:
    """Get all registered users."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@handle_db_errors
async def get_users_for_digest() -> list:
    """Get users who have digest enabled."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE digest_enabled = 1")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@handle_db_errors
async def get_users_for_daily_quote() -> list:
    """Get users who have daily quote enabled."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE daily_quote_enabled = 1")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ============ Quote functions ============

@handle_db_errors
async def save_quote(user_id: int, text: str, url: str = None, title: str = None,
                     author: str = None, domain: str = None, tags: list = None) -> int:
    """Save a new quote for a user."""
    if not text or not text.strip():
        raise ValueError("Quote text cannot be empty")

    tags_str = ",".join(tags) if tags else None
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute(
            """INSERT INTO quotes (user_id, text, url, source_title, source_author, source_domain, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, text.strip(), url, title, author, domain, tags_str)
        )
        await db.commit()
        quote_id = cursor.lastrowid
        logger.debug(f"Saved quote {quote_id} for user {user_id}")
        return quote_id


@handle_db_errors
async def delete_quote(user_id: int, quote_id: int) -> bool:
    """Delete a quote by ID. Returns True if deleted."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM quotes WHERE id = ? AND user_id = ?",
            (quote_id, user_id)
        )
        await db.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.debug(f"Deleted quote {quote_id} for user {user_id}")
        return deleted


@handle_db_errors
async def get_quote_by_id(user_id: int, quote_id: int) -> dict | None:
    """Get a quote by ID for a specific user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM quotes WHERE id = ? AND user_id = ?",
            (quote_id, user_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


@handle_db_errors
async def get_random_quotes(user_id: int, n: int = 10, use_spaced_repetition: bool = True) -> list:
    """
    Get random quotes for a user, optionally weighted by spaced repetition.

    Spaced repetition prioritizes quotes that:
    1. Have never been shown
    2. Haven't been shown in 30+ days
    3. Haven't been shown in 7+ days
    4. All others, sorted by times_shown (least shown first)
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        if use_spaced_repetition:
            cursor = await db.execute("""
                SELECT * FROM quotes
                WHERE user_id = ?
                ORDER BY
                    CASE
                        WHEN last_shown IS NULL THEN 0
                        WHEN last_shown < datetime('now', '-30 days') THEN 1
                        WHEN last_shown < datetime('now', '-7 days') THEN 2
                        ELSE 3
                    END,
                    times_shown ASC,
                    RANDOM()
                LIMIT ?
            """, (user_id, n))
        else:
            cursor = await db.execute(
                "SELECT * FROM quotes WHERE user_id = ? ORDER BY RANDOM() LIMIT ?",
                (user_id, n)
            )

        rows = await cursor.fetchall()
        quotes = [dict(row) for row in rows]

        # Update last_shown and times_shown for retrieved quotes
        if quotes:
            quote_ids = [q["id"] for q in quotes]
            placeholders = ",".join("?" * len(quote_ids))
            await db.execute(f"""
                UPDATE quotes
                SET last_shown = CURRENT_TIMESTAMP, times_shown = times_shown + 1
                WHERE id IN ({placeholders})
            """, quote_ids)
            await db.commit()

        return quotes


@handle_db_errors
async def get_last_quotes(user_id: int, n: int = 5) -> list:
    """Get the most recently added quotes for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM quotes WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, n)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@handle_db_errors
async def get_quote_count(user_id: int) -> int:
    """Get total number of quotes for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM quotes WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row[0]


@handle_db_errors
async def get_quotes_this_week(user_id: int) -> int:
    """Get number of quotes added in the last 7 days."""
    week_ago = datetime.now() - timedelta(days=7)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM quotes WHERE user_id = ? AND created_at >= ?",
            (user_id, week_ago.isoformat())
        )
        row = await cursor.fetchone()
        return row[0]


@handle_db_errors
async def search_quotes(user_id: int, keyword: str) -> list:
    """Search quotes by keyword (case-insensitive)."""
    if not keyword or not keyword.strip():
        return []

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM quotes WHERE user_id = ? AND text LIKE ? ORDER BY created_at DESC LIMIT 10",
            (user_id, f"%{keyword.strip()}%")
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@handle_db_errors
async def get_quotes_by_tag(user_id: int, tag: str) -> list:
    """Get quotes with a specific tag."""
    if not tag or not tag.strip():
        return []

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM quotes WHERE user_id = ? AND tags LIKE ? ORDER BY created_at DESC LIMIT 10",
            (user_id, f"%{tag.strip()}%")
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@handle_db_errors
async def get_quotes_by_source(user_id: int, domain: str) -> list:
    """Get quotes from a specific source domain."""
    if not domain or not domain.strip():
        return []

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM quotes WHERE user_id = ? AND source_domain LIKE ? ORDER BY created_at DESC LIMIT 10",
            (user_id, f"%{domain.strip()}%")
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@handle_db_errors
async def toggle_favorite(user_id: int, quote_id: int) -> bool | None:
    """Toggle favorite status. Returns new status, or None if quote not found."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT is_favorite FROM quotes WHERE id = ? AND user_id = ?",
            (quote_id, user_id)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        new_status = 0 if row[0] else 1
        await db.execute(
            "UPDATE quotes SET is_favorite = ? WHERE id = ? AND user_id = ?",
            (new_status, quote_id, user_id)
        )
        await db.commit()
        logger.debug(f"Toggled favorite for quote {quote_id}: {bool(new_status)}")
        return bool(new_status)


@handle_db_errors
async def get_favorite_quotes(user_id: int) -> list:
    """Get all favorite quotes for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM quotes WHERE user_id = ? AND is_favorite = 1 ORDER BY created_at DESC",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@handle_db_errors
async def get_top_tags(user_id: int, limit: int = 5) -> list:
    """Get the most used tags for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT tags FROM quotes WHERE user_id = ? AND tags IS NOT NULL",
            (user_id,)
        )
        rows = await cursor.fetchall()

    tag_counts = {}
    for row in rows:
        if row[0]:
            for tag in row[0].split(","):
                tag = tag.strip()
                if tag:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_tags[:limit]


@handle_db_errors
async def is_duplicate(user_id: int, text: str, minutes: int = 1) -> bool:
    """Check if an identical quote was saved recently."""
    if not text:
        return False

    cutoff = datetime.now() - timedelta(minutes=minutes)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM quotes WHERE user_id = ? AND text = ? AND created_at >= ?",
            (user_id, text.strip(), cutoff.isoformat())
        )
        row = await cursor.fetchone()
        return row[0] > 0


@handle_db_errors
async def export_all_quotes(user_id: int) -> str:
    """Export all quotes for a user as JSON string."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM quotes WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = await cursor.fetchall()
        quotes = [dict(row) for row in rows]

    logger.info(f"Exported {len(quotes)} quotes for user {user_id}")
    return json.dumps(quotes, indent=2, default=str)
