import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from config import (
    DAILY_QUOTE_ENABLED,
    DIGEST_COUNT,
    DIGEST_ENABLED,
    get_daily_quote_schedule,
    get_digest_schedule,
)
from src.bot import format_quote
from src.database import (
    get_quote_count,
    get_random_quotes,
    get_users_for_daily_quote,
    get_users_for_digest,
)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def send_digest_to_user(bot: Bot, user_id: int):
    """Send the weekly digest to a specific user."""
    quotes = await get_random_quotes(user_id, DIGEST_COUNT)
    total = await get_quote_count(user_id)

    if not quotes:
        await bot.send_message(
            chat_id=user_id,
            text="Your Weekly Quote Digest\n\nNo quotes saved yet. Start sending me quotes to build your collection!"
        )
        return

    message = "Your Weekly Quote Digest\n\n"

    for i, quote in enumerate(quotes, 1):
        message += f"{i}. {format_quote(quote)}\n\n"

    message += f"Total saved: {total} quotes"

    # Telegram has a 4096 character limit
    if len(message) > 4000:
        message = message[:3997] + "..."

    await bot.send_message(chat_id=user_id, text=message)


async def send_daily_quote_to_user(bot: Bot, user_id: int):
    """Send a single quote of the day to a specific user."""
    quotes = await get_random_quotes(user_id, 1)

    if not quotes:
        return  # Don't send anything if no quotes saved

    quote = quotes[0]
    message = f"Quote of the Day\n\n{format_quote(quote)}"

    await bot.send_message(chat_id=user_id, text=message)


async def send_digest_to_all(bot: Bot):
    """Send the weekly digest to all users who have it enabled."""
    users = await get_users_for_digest()
    logger.info(f"Sending weekly digest to {len(users)} users")

    for user in users:
        try:
            await send_digest_to_user(bot, user["chat_id"])
        except Exception as e:
            logger.error(f"Failed to send digest to user {user['chat_id']}: {e}")


async def send_daily_quote_to_all(bot: Bot):
    """Send the daily quote to all users who have it enabled."""
    users = await get_users_for_daily_quote()
    logger.info(f"Sending daily quote to {len(users)} users")

    for user in users:
        try:
            await send_daily_quote_to_user(bot, user["chat_id"])
        except Exception as e:
            logger.error(f"Failed to send daily quote to user {user['chat_id']}: {e}")


def setup_scheduler(bot: Bot):
    """Set up the scheduled jobs."""

    # Weekly digest
    if DIGEST_ENABLED:
        schedule = get_digest_schedule()
        scheduler.add_job(
            send_digest_to_all,
            trigger="cron",
            day_of_week=schedule["day_of_week"],
            hour=schedule["hour"],
            minute=schedule["minute"],
            args=[bot],
            id="weekly_digest",
            replace_existing=True,
        )
        logger.info(f"Weekly digest scheduled for day {schedule['day_of_week']} at {schedule['hour']}:{schedule['minute']}")

    # Daily quote of the day
    if DAILY_QUOTE_ENABLED:
        daily_schedule = get_daily_quote_schedule()
        scheduler.add_job(
            send_daily_quote_to_all,
            trigger="cron",
            hour=daily_schedule["hour"],
            minute=daily_schedule["minute"],
            args=[bot],
            id="daily_quote",
            replace_existing=True,
        )
        logger.info(f"Daily quote scheduled at {daily_schedule['hour']}:{daily_schedule['minute']}")

    scheduler.start()
