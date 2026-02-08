import sqlite3
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

# ---------- CONFIGURAÇÕES ----------
TOKEN = "8533380179:AAEp0BVRQEzu0ygg0dUMOLQNFKlWZ51DofM"
VIP_GROUP_ID = -3616377094
GUMROAD_LINK = "https://helenavargas01.gumroad.com/l/helenavargasvip"

# ---------- FLASK ----------
app = Flask(__name__)

# ---------- BANCO DE DADOS ----------
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    paid INTEGER DEFAULT 0
)
""")
conn.commit()

# ---------- TEXTOS ----------
TEXT = {
    "welcome": (
        "👋 Welcome!\n\n"
        "🆔 Your Telegram ID:\n"
        "{id}\n\n"
        "📌 Copy and paste this ID on Gumroad checkout.\n\n"
        "💳 Purchase here:\n{link}\n\n"
        "After payment, return here and type /vip"
    ),
    "not_paid": (
        "❌ No payment found.\n\n"
        "Please complete your purchase first:\n{link}"
    ),
    "success": (
        "🎉 Access granted!\n\n"
        "Here is your VIP group access:\n{link}"
    )
}

# ---------- /START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    username = update.effective_user.username or "not_available"

    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
        (telegram_id, username)
    )
    conn.commit()

    await update.message.reply_text(
        TEXT["welcome"].format(
            id=telegram_id,
            link=GUMROAD_LINK
        )
    )

# ---------- /VIP ----------
async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id

    cursor.execute(
        "SELECT paid FROM users WHERE telegram_id=?",
        (telegram_id,)
    )
    row = cursor.fetchone()

    if not row or row[0] != 1:
        await update.message.reply_text(
            TEXT["not_paid"].format(link=GUMROAD_LINK)
        )
        return

    invite = await context.bot.create_chat_invite_link(
        chat_id=VIP_GROUP_ID,
        member_limit=1
    )

    await update.message.reply_text(
        TEXT["success"].format(link=invite.invite_link)
    )

# ---------- TELEGRAM APP ----------
tg_app = Application.builder().token(TOKEN).build()
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("vip", vip))

# ---------- WEBHOOK TELEGRAM ----------
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), tg_app.bot)
    asyncio.run(tg_app.process_update(update))
    return "ok"

# ---------- WEBHOOK GUMROAD ----------
@app.route("/webhook", methods=["POST"])
def gumroad_webhook():
    data = request.json
    print("Gumroad webhook:", data)

    if data.get("event") != "sale":
        return "ignored"

    custom_fields = data.get("custom_fields", {})
    telegram_id = custom_fields.get("Telegram ID")

    if not telegram_id:
        return "telegram id missing"

    telegram_id = int(telegram_id)

    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id, paid) VALUES (?, 1)",
        (telegram_id,)
    )
    cursor.execute(
        "UPDATE users SET paid=1 WHERE telegram_id=?",
        (telegram_id,)
    )
    conn.commit()

    return "ok"

# ---------- RUN ----------
if __name__ == "__main__":
    asyncio.run(tg_app.initialize())
    app.run(host="0.0.0.0", port=5000)