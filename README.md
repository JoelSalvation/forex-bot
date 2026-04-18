# 📈 Forex Trading Bot — EUR/USD Moving Average Crossover

A fully automated forex bot that trades EUR/USD on Exness demo,
runs free on GitHub Actions every 15 minutes, and sends Telegram alerts.

---

## Strategy
- **Indicator:** 9-period vs 21-period Moving Average Crossover
- **BUY** when fast MA crosses above slow MA
- **SELL** when fast MA crosses below slow MA
- **Stop Loss:** 20 pips | **Take Profit:** 40 pips (2:1 ratio)
- **Timeframe:** 15-minute candles

---

## Setup Instructions

### Step 1 — Add your secrets to GitHub
Go to your GitHub repo → Settings → Secrets and variables → Actions → New secret

Add these two secrets:
- `MT5_PASSWORD` → your Exness demo password
- `TELEGRAM_TOKEN` → your Telegram bot token

### Step 2 — Update bot.py
Open bot.py and confirm these values are correct:
- MT5_LOGIN (your Exness login number)
- MT5_SERVER (your Exness server)
- TELEGRAM_CHAT_ID (your Telegram chat ID)

### Step 3 — Push to GitHub
Push all files to your GitHub repository.
The bot will automatically run every 15 minutes Mon-Fri.

### Step 4 — Test manually
Go to Actions tab in GitHub → Select "Forex Trading Bot" → Click "Run workflow"

---

## Files
- `bot.py` — main trading bot logic
- `requirements.txt` — Python dependencies
- `.github/workflows/trading_bot.yml` — GitHub Actions schedule

---

## ⚠️ Risk Warning
This bot trades on a DEMO account by default. Never switch to a live
account without thoroughly testing and understanding the strategy.
Forex trading carries significant risk. Only trade with money you can afford to lose.
