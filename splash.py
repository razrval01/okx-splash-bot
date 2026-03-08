import asyncio
import json
import time
import os
import requests
from datetime import datetime, timezone
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ALERTS = [
    {"label": "🟡", "pct": 5.0,  "window_sec": 180,  "tag": "SPLASH x5%"},
    {"label": "🟠", "pct": 15.0, "window_sec": 420,  "tag": "SPLASH x15%"},
    {"label": "🔴", "pct": 50.0, "window_sec": 600,  "tag": "SPLASH x50%"},
]

MIN_VOLUME_USD = 30_000
price_history = defaultdict(list)
alerted = defaultdict(dict)


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")


def check_alerts(symbol, current_price, volume_24h):
    if volume_24h < MIN_VOLUME_USD:
        return

    now = time.time()
    history = price_history[symbol]

    for alert in ALERTS:
        window = alert["window_sec"]
        cutoff = now - window

        old_prices = [p for t, p in history if t >= cutoff]
        if not old_prices:
            continue

        oldest_price = old_prices[0]
        if oldest_price == 0:
            continue

        change_pct = (current_price - oldest_price) / oldest_price * 100

        if abs(change_pct) >= alert["pct"]:
            key = f"{symbol}_{alert['pct']}"
            last_alert = alerted[symbol].get(key, 0)

            if now - last_alert < window:
                continue

            alerted[symbol][key] = now
            direction = "▲" if change_pct > 0 else "▼"
            minutes = window // 60

            vol_str = f"${volume_24h/1_000_000:.2f}M" if volume_24h >= 1_000_000 else f"${volume_24h/1_000:.1f}K"
            utc_time = datetime.now(timezone.utc).strftime("%H:%M:%S")

            msg = (
                f"{alert['label']} {alert['tag']} | {symbol}\n"
                f"{direction} {change_pct:+.1f}% за {minutes} мин\n\n"
                f"💰 Last Price:  ${current_price:,.4f}\n"
                f"📊 Volume 24h:  {vol_str}\n"
                f"⏱ Time (UTC):  {utc_time}"
            )

            print(f"ALERT: {symbol} {change_pct:+.1f}%")
            send_telegram(msg)


def update_price(symbol, price, volume_24h):
    now = time.time()
    price_history[symbol].append((now, price))
    cutoff = now - 700
    price_history[symbol] = [(t, p) for t, p in price_history[symbol] if t >= cutoff]
    check_alerts(symbol, price, volume_24h)


async def connect_okx():
    import websockets

    volumes = {}
    last_volume_fetch = 0

    async def fetch_volumes():
        nonlocal volumes, last_volume_fetch
        try:
            r = requests.get(
                "https://www.okx.com/api/v5/market/tickers?instType=SPOT",
                timeout=15
            )
            data = r.json().get("data", [])
            for item in data:
                symbol = item.get("instId", "")
                vol = float(item.get("volCcy24h", 0)) * float(item.get("last", 0))
                volumes[symbol] = vol
            last_volume_fetch = time.time()
            print(f"Loaded {len(volumes)} tickers")
        except Exception as e:
            print(f"Volume fetch error: {e}")

    await fetch_volumes()

    symbols = [s for s, v in volumes.items() if v >= MIN_VOLUME_USD and s.endswith("-USDT")]
    print(f"Monitoring {len(symbols)} symbols")

    args = [{"channel": "tickers", "instId": s} for s in symbols]

    url = "wss://ws.okx.com:8443/ws/v5/public"

    while True:
        try:
            print("Connecting to OKX WebSocket...")
            async with websockets.connect(url, ping_interval=20) as ws:
                for i in range(0, len(args), 100):
                    batch = args[i:i+100]
                    await ws.send(json.dumps({"op": "subscribe", "args": batch}))
                    await asyncio.sleep(0.1)

                print("Subscribed. Waiting for data...")
                send_telegram("✅ OKX Splash Bot запущен\nМониторинг: " + str(len(symbols)) + " токенов")

                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=30)
                        data = json.loads(msg)

                        if "data" not in data:
                            continue

                        for ticker in data["data"]:
                            symbol = ticker.get("instId", "")
                            last = float(ticker.get("last", 0))
                            vol_ccy = float(ticker.get("volCcy24h", 0))
                            volume_usd = vol_ccy * last

                            if last > 0:
                                update_price(symbol, last, volume_usd)

                        if time.time() - last_volume_fetch > 3600:
                            await fetch_volumes()

                    except asyncio.TimeoutError:
                        await ws.ping()

        except Exception as e:
            print(f"WebSocket error: {e}")
            print("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(connect_okx()) 