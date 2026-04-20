"""
Forex Signal Bot - Moving Average Crossover Strategy
Uses free Forex API for live EUR/USD prices
Sends BUY/SELL signals to your Telegram phone
Runs free on GitHub Actions every 15 minutes
"""

import requests
import pandas as pd
import os
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "5597220888")

SYMBOL     = "EUR/USD"
FAST_MA    = 9
SLOW_MA    = 21

# Free forex API (no key needed)
API_URL = "https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X?interval=15m&range=5d"

# ─────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────
def send_telegram(message):
    """Send alert to your phone via Telegram."""
    if not TELEGRAM_TOKEN:
        print("No Telegram token found")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, data=payload, timeout=10)
        if res.status_code == 200:
            print("Telegram alert sent successfully!")
        else:
            print(f"Telegram error: {res.text}")
    except Exception as e:
        print(f"Telegram exception: {e}")

# ─────────────────────────────────────────────
# FETCH LIVE PRICE DATA
# ─────────────────────────────────────────────
def get_candles():
    """Fetch live EUR/USD 15-minute candles from Yahoo Finance (free)."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(API_URL, headers=headers, timeout=15)
        if res.status_code != 200:
            print(f"API error: {res.status_code}")
            return None

        data = res.json()
        chart = data["chart"]["result"][0]
        closes = chart["indicators"]["quote"][0]["close"]
        timestamps = chart["timestamp"]

        df = pd.DataFrame({
            "time": pd.to_datetime(timestamps, unit="s"),
            "close": closes
        })

        # Drop any rows with missing close prices
        df = df.dropna(subset=["close"])
        print(f"Fetched {len(df)} candles for {SYMBOL}")
        return df

    except Exception as e:
        print(f"Error fetching candles: {e}")
        return None

# ─────────────────────────────────────────────
# CALCULATE SIGNAL
# ─────────────────────────────────────────────
def get_signal(df):
    """
    Calculate Moving Average Crossover signal.
    Returns BUY, SELL, or HOLD.
    """
    if df is None or len(df) < SLOW_MA + 2:
        print("Not enough data to calculate signal")
        return "HOLD", 0, 0, 0

    df["fast_ma"] = df["close"].rolling(FAST_MA).mean()
    df["slow_ma"] = df["close"].rolling(SLOW_MA).mean()

    curr_price = round(df["close"].iloc[-1], 5)
    curr_fast  = round(df["fast_ma"].iloc[-1], 5)
    curr_slow  = round(df["slow_ma"].iloc[-1], 5)
    prev_fast  = df["fast_ma"].iloc[-2]
    prev_slow  = df["slow_ma"].iloc[-2]

    print(f"Current Price : {curr_price}")
    print(f"Fast MA ({FAST_MA}) : {curr_fast}")
    print(f"Slow MA ({SLOW_MA}) : {curr_slow}")

    # BUY: fast crosses above slow
    if prev_fast <= prev_slow and curr_fast > curr_slow:
        return "BUY", curr_price, curr_fast, curr_slow

    # SELL: fast crosses below slow
    if prev_fast >= prev_slow and curr_fast < curr_slow:
        return "SELL", curr_price, curr_fast, curr_slow

    return "HOLD", curr_price, curr_fast, curr_slow

# ─────────────────────────────────────────────
# CALCULATE SUGGESTED SL AND TP
# ─────────────────────────────────────────────
def calculate_levels(signal, price):
    """Suggest stop loss and take profit levels."""
    pip = 0.0001
    sl_pips = 20
    tp_pips = 40

    if signal == "BUY":
        sl = round(price - sl_pips * pip, 5)
        tp = round(price + tp_pips * pip, 5)
    else:
        sl = round(price + sl_pips * pip, 5)
        tp = round(price - tp_pips * pip, 5)

    return sl, tp

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def run_bot():
    print(f"\n{'='*40}")
    print(f"Signal Bot started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Strategy: MA Crossover {FAST_MA}/{SLOW_MA} on {SYMBOL}")
    print(f"{'='*40}\n")

    # Fetch candles
    df = get_candles()
    if df is None:
        msg = "⚠️ <b>Bot Error</b>\nCould not fetch EUR/USD price data. Will retry next run."
        send_telegram(msg)
        return

    # Get signal
    signal, price, fast_ma, slow_ma = get_signal(df)
    print(f"\nSignal: {signal}")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if signal == "BUY":
        sl, tp = calculate_levels("BUY", price)
        msg = (
            f"🟢 <b>BUY SIGNAL — EUR/USD</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📈 Action: <b>OPEN BUY</b> on Exness\n"
            f"💰 Entry Price: <b>{price}</b>\n"
            f"🛑 Stop Loss: <b>{sl}</b> (-20 pips)\n"
            f"🎯 Take Profit: <b>{tp}</b> (+40 pips)\n"
            f"📊 Lot Size: <b>0.01</b> (minimum)\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Fast MA: {fast_ma} | Slow MA: {slow_ma}\n"
            f"⏰ {now}"
        )
        send_telegram(msg)

    elif signal == "SELL":
        sl, tp = calculate_levels("SELL", price)
        msg = (
            f"🔴 <b>SELL SIGNAL — EUR/USD</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📉 Action: <b>OPEN SELL</b> on Exness\n"
            f"💰 Entry Price: <b>{price}</b>\n"
            f"🛑 Stop Loss: <b>{sl}</b> (+20 pips)\n"
            f"🎯 Take Profit: <b>{tp}</b> (-40 pips)\n"
            f"📊 Lot Size: <b>0.01</b> (minimum)\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Fast MA: {fast_ma} | Slow MA: {slow_ma}\n"
            f"⏰ {now}"
        )
        send_telegram(msg)

    else:
        # No signal — just print, don't spam Telegram
        print(f"No crossover signal. Market ranging. Price: {price}")
        print("No Telegram alert sent (HOLD = no action needed)")

    print("\nBot finished.")

if __name__ == "__main__":
    run_bot()
