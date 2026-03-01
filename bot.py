import asyncio
import os
import threading
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------- CONFIG ----------
TOKEN = os.environ.get("BOT_TOKEN")
FANSLY_FEET_LINK = "https://fansly.com/Viniz_"

# ---------- FLASK ----------
app = Flask(__name__)

# ---------- BOT ----------
tg_app = Application.builder().token(TOKEN).build()

# ---------- MESSAGE FUNCTION ----------
async def send_feet_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✨ Unlock My Private Feet Room ✨", url=FANSLY_FEET_LINK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "So… you found your weakness? 🦶😈\n\n"
        "Good.\n\n"
        "Behind this button there’s a private space where I don't hold back...\n\n"
        "•🔥Slow teasing\n"
        "•💦Intimate close-ups\n"
        "• Custom experiences just for you\n\n"
        "Not everyone gets access.\n"
        "Only the ones who dare to click.\n\n"
        "Ready?",
        reply_markup=reply_markup
    )

# ---------- GET CHAT ID ----------
async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type

    await update.message.reply_text(
        f"📌 Chat ID:\n\n"
        f"ID: {chat_id}\n"
        f"Type: {chat_type}"
    )

# ---------- HANDLERS ----------
tg_app.add_handler(CommandHandler("start", send_feet_link))
tg_app.add_handler(CommandHandler("feet", send_feet_link))
tg_app.add_handler(CommandHandler("id", get_chat_id))

# ---------- EVENT LOOP ----------
loop = asyncio.new_event_loop()

def run_bot():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(tg_app.initialize())
    loop.run_until_complete(tg_app.start())
    loop.run_until_complete(
        tg_app.bot.set_webhook(f"https://telegram-bot-ncgp.onrender.com/{TOKEN}")
    )
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