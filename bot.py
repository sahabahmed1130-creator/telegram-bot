import yfinance as yf
import ta
import datetime
import time
import numpy as np
import json
import asyncio
import threading

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "8472815895:AAFwbXFwNSmsnZBckNtz55d_qVCacThD8e0"
VIP_KEY = "786VIP"

chat_id = None
FILE = "signals.json"

pairs = [
    "EURUSD=X","GBPUSD=X","USDJPY=X",
    "AUDUSD=X","USDCAD=X","EURJPY=X","GBPJPY=X"
]

wins = 0
loss = 0
last_trade_lost = False


# ===== TIME FILTER =====
def allowed_time():
    pkt = datetime.datetime.utcnow() + datetime.timedelta(hours=5)
    return 11 <= pkt.hour < 22


# ===== SAVE HISTORY =====
def save_signal(data):
    try:
        with open(FILE,"r") as f:
            old=json.load(f)
    except:
        old=[]

    old.append(data)

    with open(FILE,"w") as f:
        json.dump(old,f,indent=4)


# ===== ANALYSIS =====
def analyze_pair(pair):

    data5 = yf.download(pair, interval="5m", period="1d")
    data1 = yf.download(pair, interval="1m", period="1d")

    if len(data5)<60 or len(data1)<60:
        return None

    close5=data5["Close"]
    open5=data5["Open"]
    high5=data5["High"]
    low5=data5["Low"]
    close1=data1["Close"]

    ema20=ta.trend.ema_indicator(close5,20)
    ema50=ta.trend.ema_indicator(close5,50)
    rsi=ta.momentum.rsi(close5,14)

    last=len(close5)-2

    trend_up=ema20[last]>ema50[last]
    trend_down=ema20[last]<ema50[last]

    body=abs(close5[last]-open5[last])
    vol=np.std(close5[-10:])
    strong_body=body>vol*0.35

    wick=(high5[last]-low5[last])-body
    fake_breakout=wick>body*1.5

    movement=abs(close5[last]-close5[last-1])
    strong_move=movement>vol*0.4

    ema1=ta.trend.ema_indicator(close1,20)
    mtf_up=close1.iloc[-2]>ema1.iloc[-2]
    mtf_down=close1.iloc[-2]<ema1.iloc[-2]

    score=0

    if trend_up: score+=25
    if rsi[last]>55: score+=25
    if strong_body: score+=20
    if mtf_up: score+=20
    if strong_move: score+=10
    if fake_breakout: score-=20

    if score>=70:
        return ("CALL",pair.replace("=X",""),score,"STRONG")

    score=0

    if trend_down: score+=25
    if rsi[last]<45: score+=25
    if strong_body: score+=20
    if mtf_down: score+=20
    if strong_move: score+=10
    if fake_breakout: score-=20

    if score>=70:
        return ("PUT",pair.replace("=X",""),score,"STRONG")

    return None


def fallback():
    return ("CALL","EURUSD",50,"WEAK ⚠️")


# ===== TELEGRAM START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global chat_id

    if context.args and context.args[0] == VIP_KEY:
        chat_id = update.effective_chat.id
        await update.message.reply_text("✅ ULTRA VIP Activated")
    else:
        await update.message.reply_text("❌ Wrong VIP Key")


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📊 Wins: {wins} | Loss: {loss}")


# ===== SIGNAL LOOP =====
def signal_loop(app):

    global chat_id,last_trade_lost
    last_minute=None

    while True:

        if chat_id is None:
            time.sleep(2)
            continue

        if not allowed_time():
            time.sleep(30)
            continue

        now=datetime.datetime.utcnow()

        if now.minute%5==4 and now.second>=55:

            if last_minute!=now.minute:

                last_minute=now.minute
                signals=[]

                for p in pairs:
                    sig=analyze_pair(p)
                    if sig:
                        signals.append(sig)

                if signals:
                    best=max(signals,key=lambda x:x[2])
                else:
                    best=fallback()

                msg=f"""
🔥 ULTRA VIP SIGNAL 🔥

PAIR: {best[1]}
TYPE: {best[0]}
QUALITY: {best[3]}
CONFIDENCE: {best[2]}%

ENTRY: NEXT CANDLE
EXPIRY: 5 MIN
"""

                asyncio.run(app.bot.send_message(chat_id, msg))

        time.sleep(1)


# ===== MAIN =====
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("report", report))

threading.Thread(target=signal_loop, args=(app,), daemon=True).start()

app.run_polling()