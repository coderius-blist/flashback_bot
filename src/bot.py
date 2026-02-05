from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from src.database import (
    delete_quote,
    export_all_quotes,
    get_favorite_quotes,
    get_last_quotes,
    get_quote_by_id,
    get_quote_count,
    get_quotes_by_source,
    get_quotes_by_tag,
    get_quotes_this_week,
    get_random_quotes,
    get_top_tags,
    is_duplicate,
    register_user,
    save_quote,
    search_quotes,
    toggle_favorite,
)
from src.metadata import fetch_metadata
from src.parser import parse_message

# How long to remember a pending URL (in minutes)
PENDING_URL_TIMEOUT = 5


def get_user_id(update: Update) -> int:
    """Get the user's chat ID."""
    return update.effective_chat.id


async def ensure_registered(update: Update) -> int:
    """Ensure user is registered and return their user_id."""
    user = update.effective_user
    user_id = update.effective_chat.id
    await register_user(
        chat_id=user_id,
        username=user.username if user else None,
        first_name=user.first_name if user else None,
    )
    return user_id


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_registered(update)

    await update.message.reply_text(
        "Welcome to ReadWiser!\n\n"
        "How to save a quote:\n"
        "1. Share a URL to me first\n"
        "2. Then send the quote text\n"
        "(Or send both together)\n\n"
        "Add #tags to categorize.\n\n"
        "Commands:\n"
        "/random - Get a random quote\n"
        "/last - Show recently saved quotes\n"
        "/digest - Get your digest now\n"
        "/stats - View your statistics\n"
        "/cancel - Clear pending URL\n\n"
        "Search:\n"
        "/search <word> - Search in quotes\n"
        "/tag <name> - Find by tag\n"
        "/source <domain> - Find by source\n\n"
        "Manage:\n"
        "/fav <id> - Toggle favorite\n"
        "/favorites - Show all favorites\n"
        "/delete <id> - Delete a quote\n"
        "/export - Export all quotes as JSON"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await ensure_registered(update)

    total = await get_quote_count(user_id)
    this_week = await get_quotes_this_week(user_id)
    favorites = len(await get_favorite_quotes(user_id))
    top_tags = await get_top_tags(user_id, 5)

    tags_text = ""
    if top_tags:
        tags_text = "\n\nTop tags:\n" + "\n".join(
            f"  #{tag}: {count}" for tag, count in top_tags
        )

    await update.message.reply_text(
        f"Your ReadWiser Stats\n\n"
        f"Total quotes: {total}\n"
        f"Added this week: {this_week}\n"
        f"Favorites: {favorites}"
        f"{tags_text}"
    )


async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await ensure_registered(update)

    quotes = await get_random_quotes(user_id, 1)
    if not quotes:
        await update.message.reply_text("No quotes saved yet. Send me some!")
        return

    quote = quotes[0]
    await update.message.reply_text(format_quote(quote, show_id=True))


async def last_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await ensure_registered(update)

    n = 5
    if context.args:
        try:
            n = min(int(context.args[0]), 10)
        except ValueError:
            pass

    quotes = await get_last_quotes(user_id, n)
    if not quotes:
        await update.message.reply_text("No quotes saved yet.")
        return

    response = f"Last {len(quotes)} quote(s):\n\n"
    for quote in quotes:
        response += f"{format_quote(quote, show_id=True)}\n\n"

    await update.message.reply_text(response[:4000])


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await ensure_registered(update)

    if not context.args:
        await update.message.reply_text("Usage: /search <keyword>")
        return

    keyword = " ".join(context.args)
    quotes = await search_quotes(user_id, keyword)

    if not quotes:
        await update.message.reply_text(f'No quotes found containing "{keyword}"')
        return

    response = f'Found {len(quotes)} quote(s) for "{keyword}":\n\n'
    for quote in quotes[:5]:
        response += f"{format_quote(quote, show_id=True)}\n\n"

    await update.message.reply_text(response[:4000])


async def tag_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await ensure_registered(update)

    if not context.args:
        await update.message.reply_text("Usage: /tag <tagname>")
        return

    tag = context.args[0].lstrip("#")
    quotes = await get_quotes_by_tag(user_id, tag)

    if not quotes:
        await update.message.reply_text(f'No quotes found with tag #{tag}')
        return

    response = f'Found {len(quotes)} quote(s) with #{tag}:\n\n'
    for quote in quotes[:5]:
        response += f"{format_quote(quote, show_id=True)}\n\n"

    await update.message.reply_text(response[:4000])


async def source_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await ensure_registered(update)

    if not context.args:
        await update.message.reply_text("Usage: /source <domain>")
        return

    domain = context.args[0]
    quotes = await get_quotes_by_source(user_id, domain)

    if not quotes:
        await update.message.reply_text(f'No quotes found from {domain}')
        return

    response = f'Found {len(quotes)} quote(s) from {domain}:\n\n'
    for quote in quotes[:5]:
        response += f"{format_quote(quote, show_id=True)}\n\n"

    await update.message.reply_text(response[:4000])


async def fav_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await ensure_registered(update)

    if not context.args:
        await update.message.reply_text("Usage: /fav <quote_id>")
        return

    try:
        quote_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid quote ID. Use a number.")
        return

    result = await toggle_favorite(user_id, quote_id)
    if result is None:
        await update.message.reply_text(f"Quote #{quote_id} not found.")
        return

    status = "added to" if result else "removed from"
    await update.message.reply_text(f"Quote #{quote_id} {status} favorites.")


async def favorites_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await ensure_registered(update)

    quotes = await get_favorite_quotes(user_id)
    if not quotes:
        await update.message.reply_text("No favorite quotes yet. Use /fav <id> to add some!")
        return

    response = f"Your {len(quotes)} favorite quote(s):\n\n"
    for quote in quotes[:10]:
        response += f"{format_quote(quote, show_id=True)}\n\n"

    if len(quotes) > 10:
        response += f"... and {len(quotes) - 10} more"

    await update.message.reply_text(response[:4000])


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await ensure_registered(update)

    if not context.args:
        await update.message.reply_text("Usage: /delete <quote_id>")
        return

    try:
        quote_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid quote ID. Use a number.")
        return

    quote = await get_quote_by_id(user_id, quote_id)
    if not quote:
        await update.message.reply_text(f"Quote #{quote_id} not found.")
        return

    success = await delete_quote(user_id, quote_id)
    if success:
        await update.message.reply_text(
            f"Deleted quote #{quote_id}:\n\"{truncate(quote['text'], 50)}\""
        )
    else:
        await update.message.reply_text("Failed to delete quote.")


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await ensure_registered(update)

    json_data = await export_all_quotes(user_id)
    count = await get_quote_count(user_id)

    if count == 0:
        await update.message.reply_text("No quotes to export.")
        return

    # Send as a document
    from io import BytesIO
    file = BytesIO(json_data.encode())
    file.name = "readwiser_quotes.json"

    await update.message.reply_document(
        document=file,
        caption=f"Exported {count} quotes"
    )


async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await ensure_registered(update)

    from src.scheduler import send_digest_to_user
    await send_digest_to_user(context.bot, user_id)


def get_pending_url(context: ContextTypes.DEFAULT_TYPE) -> tuple[str, dict] | None:
    """Get pending URL if it exists and hasn't expired."""
    pending = context.user_data.get("pending_url")
    if not pending:
        return None

    # Check if expired
    if datetime.now() - pending["timestamp"] > timedelta(minutes=PENDING_URL_TIMEOUT):
        context.user_data.pop("pending_url", None)
        return None

    return pending["url"], pending["metadata"]


def set_pending_url(context: ContextTypes.DEFAULT_TYPE, url: str, metadata: dict):
    """Store a pending URL."""
    context.user_data["pending_url"] = {
        "url": url,
        "metadata": metadata,
        "timestamp": datetime.now(),
    }


def clear_pending_url(context: ContextTypes.DEFAULT_TYPE):
    """Clear any pending URL."""
    context.user_data.pop("pending_url", None)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel pending URL."""
    await ensure_registered(update)

    if get_pending_url(context):
        clear_pending_url(context)
        await update.message.reply_text("Pending URL cleared.")
    else:
        await update.message.reply_text("Nothing to cancel.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await ensure_registered(update)

    text = update.message.text
    if not text:
        return

    parsed = parse_message(text)

    # Check if message is ONLY a URL (no quote text)
    is_url_only = parsed.url and not parsed.quote

    if is_url_only:
        # Store URL and ask for quote
        metadata = await fetch_metadata(parsed.url)
        set_pending_url(context, parsed.url, {
            "title": metadata.title,
            "author": metadata.author,
            "domain": metadata.domain,
        })

        source_info = ""
        if metadata.title:
            source_info = f'\n"{metadata.title}"'
            if metadata.domain:
                source_info += f" ({metadata.domain})"
        elif metadata.domain:
            source_info = f"\n({metadata.domain})"

        await update.message.reply_text(
            f"Got the link!{source_info}\n\n"
            f"Now send me the quote from this article.\n"
            f"(Link expires in {PENDING_URL_TIMEOUT} min, /cancel to clear)"
        )
        return

    if not parsed.quote:
        await update.message.reply_text(
            "I couldn't find a quote in your message. "
            "Send me some text to save!"
        )
        return

    # Check for duplicates
    if await is_duplicate(user_id, parsed.quote):
        await update.message.reply_text("This quote was already saved recently.")
        return

    # Check for pending URL if no URL in current message
    url = parsed.url
    title, author, domain = None, None, None

    if url:
        # URL provided in this message - fetch fresh metadata
        metadata = await fetch_metadata(url)
        title = metadata.title
        author = metadata.author
        domain = metadata.domain
        clear_pending_url(context)  # Clear any pending URL
    else:
        # Check for pending URL
        pending = get_pending_url(context)
        if pending:
            url, metadata = pending
            title = metadata.get("title")
            author = metadata.get("author")
            domain = metadata.get("domain")
            clear_pending_url(context)

    # Save to database
    quote_id = await save_quote(
        user_id=user_id,
        text=parsed.quote,
        url=url,
        title=title,
        author=author,
        domain=domain,
        tags=parsed.tags,
    )

    # Build confirmation message
    response = f'Saved (#{quote_id}): "{truncate(parsed.quote, 100)}"'

    if title or domain:
        source = title or domain
        if author:
            source += f" by {author}"
        elif domain and title:
            source += f" ({domain})"
        response += f"\nFrom: {source}"

    if parsed.tags:
        response += f"\nTags: {' '.join(f'#{t}' for t in parsed.tags)}"

    await update.message.reply_text(response)


def format_quote(quote: dict, show_id: bool = False) -> str:
    """Format a quote for display."""
    prefix = f"[#{quote['id']}] " if show_id else ""
    fav = " *" if quote.get("is_favorite") else ""
    text = f'{prefix}"{quote["text"]}"{fav}'

    source_parts = []
    if quote.get("source_title"):
        source_parts.append(quote["source_title"])
    if quote.get("source_author"):
        source_parts.append(f"by {quote['source_author']}")
    elif quote.get("source_domain"):
        source_parts.append(f"({quote['source_domain']})")

    if source_parts:
        text += f"\n  -- {' '.join(source_parts)}"

    if quote.get("url"):
        text += f"\n  {quote['url']}"

    if quote.get("tags"):
        text += f"\n  {' '.join(f'#{t}' for t in quote['tags'].split(','))}"

    return text


def truncate(text: str, length: int) -> str:
    """Truncate text to length with ellipsis."""
    if len(text) <= length:
        return text
    return text[:length - 3] + "..."


def create_bot() -> Application:
    """Create and configure the Telegram bot."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("random", random_command))
    app.add_handler(CommandHandler("last", last_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("tag", tag_command))
    app.add_handler(CommandHandler("source", source_command))
    app.add_handler(CommandHandler("fav", fav_command))
    app.add_handler(CommandHandler("favorites", favorites_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("digest", digest_command))
    app.add_handler(CommandHandler("cancel", cancel_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app
