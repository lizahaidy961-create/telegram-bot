import asyncio
import os
import threading
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------- CONFIG ----------
TOKEN = "8533380179:AAGm4C9zN_J1_C3SeMiUPr-iCv-pj3gAXhI"
FANSLY_FEET_LINK = "https://fansly.com/Viniz_"

# ---------- FLASK ----------
app = Flask(__name__)

# ---------- BOT ----------
tg_app = Application.builder().token(TOKEN).build()

# ---------- MESSAGE FUNCTION ----------
async def send_feet_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🦶 Enter My Feet World 🦶", url=FANSLY_FEET_LINK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Oh… so you like feet? 🦶😈\n\n"
        "I have something special waiting for you there…\n\n"
        "🔥 Exclusive feet content\n"
        "💦 Close-ups\n"
        "👀 Custom requests\n\n"
        "Tap below and enjoy…",
        reply_markup=reply_markup
    )

# ---------- HANDLERS ----------
tg_app.add_handler(CommandHandler("start", send_feet_link))
tg_app.add_handler(CommandHandler("feet", send_feet_link))

# ---------- EVENT LOOP ----------
loop = asyncio.new_event_loop()

def run_bot():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(tg_app.initialize())
    loop.run_until_complete(tg_app.start())
    loop.run_forever()

threading.Thread(target=run_bot, daemon=True).start()

# ---------- TELEGRAM WEBHOOK ----------
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), tg_app.bot)
    asyncio.run_coroutine_threadsafe(
        tg_app.process_update(update),
        loop
    )
    return "ok", 200

@app.route("/")
def home():
    return "Bot online", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)