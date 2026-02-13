import yfinance as yf
import ta
import datetime
import asyncio
import os

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("8472815895:AAFwbXFwNSmsnZBckNtz55d_qVCacThD8e0")
VIP_KEY = "786VIP"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

chat_id = None

pairs = [
    "EURUSD=X","GBPUSD=X","USDJPY=X",
    "AUDUSD=X","USDCAD=X","EURJPY=X","GBPJPY=X"
]

# ---------- TIME FILTER ----------
def allowed_time():
    pkt = datetime.datetime.utcnow() + datetime.timedelta(hours=5)
    return 11 <= pkt.hour < 22

# ---------- ANALYSIS ----------
def analyze_pair(pair):
    try:
        data = yf.download(pair, interval="5m", period="1d", progress=False)

        if len(data) < 60:
            return None

        close = data["Close"]

        ema20 = ta.trend.ema_indicator(close, 20)
        ema50 = ta.trend.ema_indicator(close, 50)
        rsi = ta.momentum.rsi(close, 14)

        last = len(close) - 2

        if ema20.iloc[last] > ema50.iloc[last] and rsi.iloc[last] > 55:
            return ("CALL", pair.replace("=X",""))

        if ema20.iloc[last] < ema50.iloc[last] and rsi.iloc[last] < 45:
            return ("PUT", pair.replace("=X",""))

        return None

    except Exception as e:
        print("Analyze Error:", e)
        return None

# ---------- START COMMAND ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global chat_id

    if context.args and context.args[0] == VIP_KEY:
        chat_id = update.effective_chat.id
        await update.message.reply_text("✅ ULTRA VIP Activated")
    else:
        await update.message.reply_text("❌ Wrong VIP Key")

# ---------- SIGNAL LOOP ----------
async def signal_loop(app):
    global chat_id
    last_minute = None

    while True:
        try:
            if chat_id is None:
                await asyncio.sleep(5)
                continue

            if not allowed_time():
                await asyncio.sleep(60)
                continue

            now = datetime.datetime.utcnow()

            if now.minute % 5 == 4 and now.second >= 55:

                if last_minute != now.minute:
                    last_minute = now.minute

                    for p in pairs:
                        sig = analyze_pair(p)

                        if sig:
                            msg = f"""
🔥 ULTRA VIP SIGNAL 🔥

PAIR: {sig[1]}
TYPE: {sig[0]}
ENTRY: NEXT CANDLE
EXPIRY: 5 MIN
"""
                            await app.bot.send_message(chat_id, msg)
                            break

            await asyncio.sleep(1)

        except Exception as e:
            print("Loop Error:", e)
            await asyncio.sleep(5)

# ---------- MAIN ----------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    asyncio.create_task(signal_loop(app))

    print("Bot Running...")

    await app.run_polling()

asyncio.run(main())
