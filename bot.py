import sqlite3
import asyncio
import threading
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------- CONFIG ----------
TOKEN = "8533380179:AAEp0BVRQEzu0ygg0dUMOLQNFKlWZ51DofM"
VIP_GROUP_ID = -3616377094
GUMROAD_LINK = "https://helenavargas01.gumroad.com/l/helenavargasvip"

# ---------- FLASK ----------
app = Flask(__name__)

# ---------- DATABASE ----------
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

# ---------- TEXT ----------
TEXT = {
    "welcome": (
        "👋 Welcome!\n\n"
        "🆔 Your Telegram ID:\n{tid}\n\n"
        "📌 Paste this ID in Gumroad checkout\n\n"
        "💳 Buy here:\n{link}\n\n"
        "After payment, return and type /vip"
    ),
    "not_paid": "❌ Payment not found.\n\nBuy here:\n{link}",
    "success": "🎉 Access granted!\n\nVIP Group:\n{link}"
}

# ---------- BOT ----------
tg_app = Application.builder().token(TOKEN).build()

# ---------- /START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id
    username = update.effective_user.username or "none"

    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
        (tid, username)
    )
    conn.commit()

    await update.message.reply_text(
        TEXT["welcome"].format(tid=tid, link=GUMROAD_LINK)
    )

# ---------- /VIP ----------
async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id

    cursor.execute("SELECT paid FROM users WHERE telegram_id=?", (tid,))
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

tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("vip", vip))

# ---------- EVENT LOOP (THREAD SEPARADA) ----------
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
    return "ok"

# ---------- GUMROAD WEBHOOK ----------
@app.route("/webhook", methods=["POST"])
def gumroad_webhook():
    data = request.form.to_dict()
    print("Gumroad:", data)

    telegram_id = data.get("custom_fields[Telegram ID]")
    if not telegram_id:
        return "missing telegram id", 400

    cursor.execute(
        "UPDATE users SET paid=1 WHERE telegram_id=?",
        (int(telegram_id),)
    )
    conn.commit()

    return "ok"

# ---------- RUN FLASK ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
