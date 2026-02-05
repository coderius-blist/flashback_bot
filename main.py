import asyncio
import logging

from config import validate_config
from src.bot import create_bot
from src.database import init_db
from src.scheduler import setup_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main():
    # Validate configuration
    validate_config()
    logger.info("Configuration validated")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Create bot
    app = create_bot()
    logger.info("Bot created")

    # Set up scheduler
    async with app:
        setup_scheduler(app.bot)
        logger.info("Scheduler started")

        # Start polling
        logger.info("Starting bot...")
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)

        # Run until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await app.updater.stop()
            await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
