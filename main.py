import os
import yfinance as yf
import numpy as np
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from groq import Groq

# Ambil API key dari Replit Secrets
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

# --- Fungsi Menghitung Indikator ---
def hitung_rsi(close, period=14):
    close = np.array(close)
    delta = np.diff(close)

    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = np.mean(gain[-period:])
    avg_loss = np.mean(loss[-period:])

    if avg_loss == 0:
        return 100  # Overbought parah

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return round(rsi, 2)

def hitung_ma(close, period=20):
    if len(close) < period:
        return None
    return round(np.mean(close[-period:]), 2)

def hitung_macd(close):
    close = np.array(close)

    ema12 = close[-12:].mean()
    ema26 = close[-26:].mean()
    macd = ema12 - ema26
    return round(macd, 3)


# --- Command Utama ---
async def analisa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Format:\n/analisa BBCA")
        return

    kode = context.args[0].upper() + ".JK"

    # Ambil data 3 bulan terakhir
    data = yf.Ticker(kode).history(period="3mo")

    if data.empty:
        await update.message.reply_text("Saham tidak ditemukan di IDX bang.")
        return

    close = data["Close"].tolist()
    last_price = close[-1]

    # Hitung indikator
    rsi = hitung_rsi(close)
    ma20 = hitung_ma(close, 20)
    macd = hitung_macd(close)

    indikator_text = f"""
📊 *Indikator Teknis*
RSI: {rsi}
MA20: {ma20}
MACD: {macd}
"""

    # Prompt untuk AI Groq
    prompt = f"""
Kamu adalah analis saham profesional.
Analisa saham {kode} berdasarkan:

Harga penutupan 3 bulan terakhir:
{close}

Harga terakhir: {last_price}

Indikator teknikal:
- RSI: {rsi}
- MA20: {ma20}
- MACD: {macd}

Berikan analisa:
1. Tren jangka pendek & menengah
2. Support - Resistance
3. Risiko
4. Catatan penting
5. Kesimpulan (tanpa ajakan beli/jual)
"""

    # Generate AI response
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": prompt}]
    )

    analisa_ai = response.choices[0].message["content"]

    await update.message.reply_text(indikator_text + "\n" + analisa_ai, parse_mode="Markdown")


# --- Setup Bot ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("analisa", analisa))

if __name__ == "__main__":
    print("Bot nyala bang 🔥")
    app.run_polling()