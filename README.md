# HANZLA AI — Quotex Signals (starter)

This is a beginner starter project for a Telegram bot that calculates transparent technical-indicator signals from **normal-market FX data**.

## Important limitations
- It does **not** connect to Quotex, place trades, or read Quotex account data.
- It does **not** use Quotex OTC prices. OTC is deliberately disabled until you have a reliable, permitted data source matching the broker's OTC feed.
- CALL / PUT / WAIT are experimental indicator outputs, not guaranteed predictions, financial advice, or win probabilities.
- Do not use real money based on these outputs. Forward-test and backtest first.

## 1. Create a Telegram bot
1. Open https://t.me/BotFather in Telegram.
2. Send `/newbot` and follow its instructions.
3. Copy the bot token. Keep it private; never post it in a chat or public code repository.

## 2. Get a market-data API key
Create an account with Twelve Data: https://twelvedata.com/
Check its current pricing, supported FX symbols, and whether 1-minute, 5-minute, and 15-minute candles are included in your plan. The free tier may have limits.

## 3. Run on a computer
Install Python 3.10+.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in both keys:
- `TELEGRAM_BOT_TOKEN`
- `TWELVEDATA_API_KEY`

Then run:

```bash
python bot.py
```

## 4. Try commands in Telegram
- `/start`
- `/pairs`
- `/signal EUR/USD 1m`
- `/signal GBP/USD 5m`
- `/signal USD/JPY 15m`

## 5. Before expanding
1. Save each signal with timestamp and subsequent price outcome.
2. Backtest across different market regimes.
3. Include data costs, spread, slippage, and the exact broker settlement rules.
4. Compare signals against the actual Quotex quote only if you can lawfully and reliably obtain it.
5. Do not advertise a win rate until it is measured on a sufficiently large out-of-sample dataset.

## Why OTC is not enabled
OTC feeds may be broker-specific and can differ from external FX prices. A signal based on an unrelated price feed would be misleading.
