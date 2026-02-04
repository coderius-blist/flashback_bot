import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "quotes.db"

# Telegram settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Weekly digest settings
DIGEST_ENABLED = os.getenv("DIGEST_ENABLED", "true").lower() == "true"
DIGEST_DAY = os.getenv("DIGEST_DAY", "sunday").lower()
DIGEST_TIME = os.getenv("DIGEST_TIME", "10:00")
DIGEST_COUNT = int(os.getenv("DIGEST_COUNT", "10"))

# Daily quote of the day settings
DAILY_QUOTE_ENABLED = os.getenv("DAILY_QUOTE_ENABLED", "true").lower() == "true"
DAILY_QUOTE_TIME = os.getenv("DAILY_QUOTE_TIME", "09:00")

# Validate required settings
def validate_config():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is required. Set it in .env file.")

# Day name to cron day mapping
DAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

def get_digest_schedule():
    day = DAY_MAP.get(DIGEST_DAY, 6)
    hour, minute = DIGEST_TIME.split(":")
    return {"day_of_week": day, "hour": int(hour), "minute": int(minute)}

def get_daily_quote_schedule():
    hour, minute = DAILY_QUOTE_TIME.split(":")
    return {"hour": int(hour), "minute": int(minute)}
