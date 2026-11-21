import os
import logging
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

load_dotenv()

BOT_TOKEN = os.getenv("9115564233:AAHEKhp_ec3DDK0sOUlZ8N1SAvq4srbdD-c", "").strip()
TWELVE_DATA_KEY = os.getenv("36be030346f94bbbb769214536b36918", "").strip()

# Start with a small, liquid set of normal-market FX pairs.
# Add pairs only after confirming your data provider supports them.
PAIRS = {
    "EUR/USD": "EUR/USD",
    "GBP/USD": "GBP/USD",
    "USD/JPY": "USD/JPY",
    "AUD/USD": "AUD/USD",
    "USD/CAD": "USD/CAD",
    "USD/CHF": "USD/CHF",
}
INTERVALS = {"1m": "1min", "5m": "5min", "15m": "15min"}

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("hanzla-ai")


def fetch_candles(symbol: str, interval: str) -> pd.DataFrame:
    """Fetch normal-market candles from Twelve Data. No OTC feed is used."""
    if not TWELVE_DATA_KEY:
        raise RuntimeError("Missing TWELVEDATA_API_KEY in .env")

    response = requests.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": symbol,
            "interval": interval,
            "outputsize": 120,
            "apikey": TWELVE_DATA_KEY,
            "format": "JSON",
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("status") == "error" or "values" not in payload:
        message = payload.get("message", "No candle data returned")
        raise RuntimeError(message)

    df = pd.DataFrame(payload["values"])
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"]).sort_values("datetime").reset_index(drop=True)

    if len(df) < 60:
        raise RuntimeError("Not enough candles for indicator analysis")
    return df


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def analyze(df: pd.DataFrame) -> dict:
    close = df["close"]
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    macd_line = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    rsi_value = float(rsi(close).iloc[-1])

    # A simple transparent ruleset, not a trained AI model.
    score = 0
    reasons = []

    if ema9.iloc[-1] > ema21.iloc[-1]:
        score += 1
        reasons.append("EMA 9 above EMA 21")
    else:
        score -= 1
        reasons.append("EMA 9 below EMA 21")

    if close.iloc[-1] > ema50.iloc[-1]:
        score += 1
        reasons.append("Price above EMA 50")
    else:
        score -= 1
        reasons.append("Price below EMA 50")

    if macd_line.iloc[-1] > macd_signal.iloc[-1]:
        score += 1
        reasons.append("MACD above signal")
    else:
        score -= 1
        reasons.append("MACD below signal")

    # Avoid chasing extreme RSI readings.
    if 50 <= rsi_value <= 68:
        score += 1
        reasons.append("RSI supports upward momentum")
    elif 32 <= rsi_value < 50:
        score -= 1
        reasons.append("RSI supports downward momentum")
    else:
        reasons.append("RSI is extended; no extra score")

    if score >= 3:
        signal = "CALL"
    elif score <= -3:
        signal = "PUT"
    else:
        signal = "WAIT"

    return {
        "signal": signal,
        "score": score,
        "rsi": rsi_value,
        "price": float(close.iloc[-1]),
        "reasons": reasons,
        "candle_time": str(df["datetime"].iloc[-1]),
    }


def format_signal(pair: str, interval_label: str, result: dict) -> str:
    emoji = {"CALL": "🟢", "PUT": "🔴", "WAIT": "🟡"}[result["signal"]]
    reasons = "\n".join(f"• {item}" for item in result["reasons"])
    return (
        f"🤖 *HANZLA AI — DEMO SIGNAL*\n\n"
        f"*Pair:* `{pair}`\n"
        f"*Chart interval:* `{interval_label}`\n"
        f"*Indicator result:* {emoji} *{result['signal']}*\n"
        f"*Rule score:* `{result['score']}/4` (not a probability)\n"
        f"*Latest reference price:* `{result['price']}`\n"
        f"*RSI (14):* `{result['rsi']:.1f}`\n"
        f"*Latest candle time:* `{result['candle_time']}`\n\n"
        f"*Reasons:*\n{reasons}\n\n"
        f"⚠️ This is experimental technical analysis, not a prediction or guaranteed win. "
        f"Check the live broker price yourself. No OTC data is used. Do not trade real money "
        f"until you have forward-tested and recorded results."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Get demo signal", callback_data="signal:EUR/USD:1m")],
        [InlineKeyboardButton("⏱ 5-minute analysis", callback_data="signal:EUR/USD:5m")],
        [InlineKeyboardButton("⏱ 15-minute analysis", callback_data="signal:EUR/USD:15m")],
        [InlineKeyboardButton("📚 Supported pairs", callback_data="pairs")],
    ]
    await update.message.reply_text(
        "Welcome to *HANZLA AI — QUOTEX SIGNALS*\\n\\n"
        "This bot analyzes normal-market FX candles and returns CALL / PUT / WAIT "
        "indicator results for education and demo testing.\\n\\n"
        "OTC is disabled because this project does not have a verified Quotex OTC price feed.\\n"
        "Use /signal EUR/USD 1m or /signal GBP/USD 5m.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def pairs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Supported normal-market pairs:*\n" + "\n".join(f"• `{p}`" for p in PAIRS),
        parse_mode="Markdown",
    )


async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    pair = args[0].upper().replace("-", "/") if len(args) >= 1 else "EUR/USD"
    interval_label = args[1].lower() if len(args) >= 2 else "1m"

    if pair not in PAIRS:
        await update.message.reply_text("Unsupported pair. Use /pairs to see the available pairs.")
        return
    if interval_label not in INTERVALS:
        await update.message.reply_text("Choose interval: 1m, 5m or 15m.")
        return

    msg = await update.message.reply_text("⏳ Fetching candles and calculating indicators...")
    try:
        candles = fetch_candles(PAIRS[pair], INTERVALS[interval_label])
        result = analyze(candles)
        await msg.edit_text(format_signal(pair, interval_label, result), parse_mode="Markdown")
    except Exception as exc:
        log.exception("Signal request failed")
        await msg.edit_text(
            "Could not generate a signal right now. Check your data-provider plan/API key "
            "or try again later. Details: " + str(exc)[:250]
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "pairs":
        await query.message.reply_text(
            "Supported normal-market pairs:\\n" + "\\n".join(PAIRS.keys())
        )
        return
    if query.data.startswith("signal:"):
        _, pair, interval_label = query.data.split(":")
        # Reuse the same analysis flow for inline buttons.
        try:
            candles = fetch_candles(PAIRS[pair], INTERVALS[interval_label])
            result = analyze(candles)
            await query.message.reply_text(
                format_signal(pair, interval_label, result), parse_mode="Markdown"
            )
        except Exception as exc:
            await query.message.reply_text("Signal unavailable: " + str(exc)[:250])


def main():
    if not BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in your .env file first.")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pairs", pairs_command))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    log.info("HANZLA AI bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
