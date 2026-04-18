"""
Forex Trading Bot - Moving Average Crossover Strategy
Trades EUR/USD on Exness Demo via MT5
Sends Telegram alerts on every trade
Designed to run on GitHub Actions (free, no server needed)
"""

import MetaTrader5 as mt5
import pandas as pd
import requests
from datetime import datetime
import time

# ─────────────────────────────────────────────
# CONFIGURATION — update these values
# ─────────────────────────────────────────────
MT5_LOGIN    = 435473206
MT5_PASSWORD = "$alvation247Ai"   # ← update after changing on Exness
MT5_SERVER   = "Exness-MT5Trial9"

TELEGRAM_TOKEN   = "8681646952:AAFw0Tq5IAN6rJ_ecwfdDpr-2jS2aD-R_CY"   # ← update after revoking old one
TELEGRAM_CHAT_ID = "5597220888"

SYMBOL     = "EURUSDm"   # Exness demo uses 'm' suffix e.g. EURUSDm
TIMEFRAME  = mt5.TIMEFRAME_M15   # 15-minute candles
FAST_MA    = 9    # Fast moving average period
SLOW_MA    = 21   # Slow moving average period
LOT_SIZE   = 0.01  # Minimum lot size — safe for beginners
STOP_LOSS_PIPS   = 20   # Stop loss in pips
TAKE_PROFIT_PIPS = 40   # Take profit in pips (2:1 reward/risk)

# ─────────────────────────────────────────────
# TELEGRAM ALERT FUNCTION
# ─────────────────────────────────────────────
def send_telegram(message):
    """Send a message to your Telegram phone."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

# ─────────────────────────────────────────────
# CONNECT TO MT5
# ─────────────────────────────────────────────
def connect_mt5():
    """Initialize and login to MetaTrader 5."""
    if not mt5.initialize():
        print("MT5 initialize failed")
        return False
    login_result = mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
    if not login_result:
        print(f"MT5 login failed: {mt5.last_error()}")
        return False
    print(f"Connected to MT5 | Account: {MT5_LOGIN} | Server: {MT5_SERVER}")
    return True

# ─────────────────────────────────────────────
# GET PRICE DATA & CALCULATE MOVING AVERAGES
# ─────────────────────────────────────────────
def get_signal():
    """
    Fetch the last 100 candles and calculate Fast/Slow MA.
    Returns 'BUY', 'SELL', or 'HOLD'.
    """
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 100)
    if rates is None or len(rates) < SLOW_MA + 2:
        print("Not enough candle data")
        return "HOLD"

    df = pd.DataFrame(rates)
    df["fast_ma"] = df["close"].rolling(FAST_MA).mean()
    df["slow_ma"] = df["close"].rolling(SLOW_MA).mean()

    # Current candle (index -1) and previous candle (index -2)
    curr_fast = df["fast_ma"].iloc[-1]
    curr_slow = df["slow_ma"].iloc[-1]
    prev_fast = df["fast_ma"].iloc[-2]
    prev_slow = df["slow_ma"].iloc[-2]

    # BUY signal: fast MA crosses ABOVE slow MA
    if prev_fast <= prev_slow and curr_fast > curr_slow:
        return "BUY"

    # SELL signal: fast MA crosses BELOW slow MA
    if prev_fast >= prev_slow and curr_fast < curr_slow:
        return "SELL"

    return "HOLD"

# ─────────────────────────────────────────────
# CHECK FOR EXISTING OPEN TRADE
# ─────────────────────────────────────────────
def has_open_trade():
    """Return True if bot already has an open position on SYMBOL."""
    positions = mt5.positions_get(symbol=SYMBOL)
    return positions is not None and len(positions) > 0

# ─────────────────────────────────────────────
# CLOSE ALL OPEN TRADES ON SYMBOL
# ─────────────────────────────────────────────
def close_all_trades():
    """Close all open positions on SYMBOL."""
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return
    for pos in positions:
        direction = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(SYMBOL).bid if direction == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(SYMBOL).ask
        request = {
            "action":    mt5.TRADE_ACTION_DEAL,
            "symbol":    SYMBOL,
            "volume":    pos.volume,
            "type":      direction,
            "position":  pos.ticket,
            "price":     price,
            "deviation": 20,
            "magic":     234000,
            "comment":   "Bot close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            profit = pos.profit
            msg = (
                f"🔴 <b>TRADE CLOSED</b>\n"
                f"Symbol: {SYMBOL}\n"
                f"Profit: {'🟢 +' if profit >= 0 else '🔴 '}{profit:.2f} USD\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            send_telegram(msg)
            print(f"Trade closed | Profit: {profit:.2f}")

# ─────────────────────────────────────────────
# PLACE A TRADE
# ─────────────────────────────────────────────
def place_trade(signal):
    """Place a BUY or SELL market order with SL and TP."""
    tick = mt5.symbol_info_tick(SYMBOL)
    info = mt5.symbol_info(SYMBOL)
    if tick is None or info is None:
        print(f"Could not get symbol info for {SYMBOL}")
        return

    point = info.point
    digits = info.digits

    if signal == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
        sl    = round(price - STOP_LOSS_PIPS * point * 10, digits)
        tp    = round(price + TAKE_PROFIT_PIPS * point * 10, digits)
    else:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
        sl    = round(price + STOP_LOSS_PIPS * point * 10, digits)
        tp    = round(price - TAKE_PROFIT_PIPS * point * 10, digits)

    request = {
        "action":    mt5.TRADE_ACTION_DEAL,
        "symbol":    SYMBOL,
        "volume":    LOT_SIZE,
        "type":      order_type,
        "price":     price,
        "sl":        sl,
        "tp":        tp,
        "deviation": 20,
        "magic":     234000,
        "comment":   f"Bot {signal}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        emoji = "🟢" if signal == "BUY" else "🔴"
        msg = (
            f"{emoji} <b>TRADE OPENED: {signal}</b>\n"
            f"Symbol: {SYMBOL}\n"
            f"Price: {price}\n"
            f"Stop Loss: {sl}\n"
            f"Take Profit: {tp}\n"
            f"Lot: {LOT_SIZE}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_telegram(msg)
        print(f"Trade placed: {signal} at {price}")
    else:
        error_msg = f"⚠️ Trade failed: {result.comment} (code {result.retcode})"
        send_telegram(error_msg)
        print(error_msg)

# ─────────────────────────────────────────────
# MAIN BOT LOGIC
# ─────────────────────────────────────────────
def run_bot():
    print(f"\n{'='*40}")
    print(f"Bot started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Strategy: MA Crossover ({FAST_MA}/{SLOW_MA}) on {SYMBOL}")
    print(f"{'='*40}\n")

    if not connect_mt5():
        send_telegram("⚠️ Bot failed to connect to MT5. Check credentials.")
        return

    signal = get_signal()
    print(f"Signal: {signal}")

    if signal == "HOLD":
        print("No trade signal. Waiting for next run.")
        mt5.shutdown()
        return

    # If a new signal contradicts open trade direction, close first
    if has_open_trade():
        positions = mt5.positions_get(symbol=SYMBOL)
        current_type = "BUY" if positions[0].type == 0 else "SELL"
        if current_type != signal:
            print(f"Signal changed to {signal}. Closing existing {current_type} trade.")
            close_all_trades()
            time.sleep(1)
            place_trade(signal)
        else:
            print(f"Already have a {current_type} trade open. Holding.")
    else:
        place_trade(signal)

    mt5.shutdown()
    print("Bot finished. MT5 disconnected.")

# ─────────────────────────────────────────────
if __name__ == "__main__":
    run_bot()
