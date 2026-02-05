# Flashback Bot

A Telegram bot for saving, organizing, and rediscovering quotes from the web. Collect quotes with automatic metadata extraction, organize them with tags, and receive curated digests.

## Features

- **Save quotes** with optional source URLs and automatic metadata extraction (title, author, domain)
- **Tag organization** using hashtags (e.g., `#wisdom #philosophy`)
- **Smart random quotes** with spaced repetition algorithm
- **Scheduled content**: weekly digests and daily "Quote of the Day"
- **Full-text search** across your quote collection
- **Favorites system** for marking important quotes
- **Export** all quotes as JSON

## Setup

### Prerequisites

- Python 3.11+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/coderius-blist/flashback_bot.git
   cd flashback_bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

4. Add your Telegram bot token to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

5. Run the bot:
   ```bash
   python main.py
   ```

## Configuration

Environment variables (set in `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Required | Bot token from BotFather |
| `DIGEST_ENABLED` | `true` | Enable weekly digest |
| `DIGEST_DAY` | `sunday` | Day for weekly digest |
| `DIGEST_TIME` | `10:00` | Time for digest (24h format) |
| `DIGEST_COUNT` | `10` | Number of quotes in digest |
| `DAILY_QUOTE_ENABLED` | `true` | Enable daily quote |
| `DAILY_QUOTE_TIME` | `09:00` | Time for daily quote |

## Usage

### Saving Quotes

**Option 1: Two-step process**
1. Send a URL
2. Send your quote text

**Option 2: One message**
```
"Your quote here" https://example.com #tag1 #tag2
```

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Show all commands |
| `/random` | Get a random quote |
| `/last [n]` | Show last N quotes (default 5) |
| `/stats` | View your statistics |
| `/search <keyword>` | Search quotes |
| `/tag <name>` | Find quotes by tag |
| `/source <domain>` | Find quotes by source |
| `/fav <id>` | Toggle favorite status |
| `/favorites` | Show all favorites |
| `/delete <id>` | Delete a quote |
| `/export` | Export quotes as JSON |
| `/digest` | Trigger weekly digest manually |
| `/cancel` | Clear pending URL |

## Deployment

### Railway

This project is deployed on [Railway](https://railway.app):

1. **Connect your repository**:
   - Go to [Railway](https://railway.app)
   - Create a new project from your GitHub repo

2. **Add environment variables**:
   - `TELEGRAM_BOT_TOKEN` - Your bot token from BotFather
   - `DIGEST_ENABLED` - (optional) `true` or `false`
   - `DIGEST_DAY` - (optional) Day of the week
   - `DIGEST_TIME` - (optional) Time in 24h format
   - `DAILY_QUOTE_ENABLED` - (optional) `true` or `false`
   - `DAILY_QUOTE_TIME` - (optional) Time in 24h format

3. **Deploy**:
   - Railway will automatically deploy on every push to main
   - The bot will start running immediately

## Project Structure

```
flashback_bot/
├── main.py           # Entry point
├── config.py         # Configuration
├── requirements.txt  # Dependencies
├── src/
│   ├── bot.py        # Telegram handlers
│   ├── database.py   # SQLite operations
│   ├── scheduler.py  # Scheduled jobs
│   ├── parser.py     # Message parsing
│   └── metadata.py   # URL metadata extraction
└── data/
    └── quotes.db     # SQLite database (auto-created)
```

## License

MIT
