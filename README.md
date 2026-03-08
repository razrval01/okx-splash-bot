# OKX Price Splash Bot

Real-time price alert bot for OKX exchange. Monitors all SPOT tokens and sends Telegram notifications on sharp price movements.

## Alert Levels

| Level | Change | Timeframe |
|-------|--------|-----------|
| 🟡 SPLASH x5% | 5% | 3 minutes |
| 🟠 SPLASH x15% | 15% | 7 minutes |
| 🔴 SPLASH x50% | 50% | 10 minutes |

## Alert Format
<img width="320" height="136" alt="image" src="https://github.com/user-attachments/assets/a71bcf0b-afc3-4922-8899-a2d276f2bcb4" />

## Setup

1. Clone the repository
2. Install dependencies: pip install requests python-dotenv websockets
3. Create .env file based on .env.example
4. Create Telegram bot via @BotFather
5. Run: python splash.py

## Configuration

Change MIN_VOLUME_USD in splash.py to filter tokens by minimum 24h volume.

Default: $50,000

## Data Source

OKX WebSocket API v5 — real-time public market data, no API key required.
