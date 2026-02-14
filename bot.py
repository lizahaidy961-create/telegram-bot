import psycopg2
import asyncio
import os
from datetime import datetime, timedelta, timezone
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------- CONFIG ----------
TOKEN = os.environ.get("8533380179:AAGm4C9zN_J1_C3SeMiUPr-iCv-pj3gAXhI")
VIP_GROUP_ID = -1003723951596
GUMROAD_LINK = "https://helenavargas01.gumroad.com/l/helenavargasvip"

# ---------- FLASK ----------
app = Flask(__name__)

# ---------- DATABASE (POSTGRES) ----------
DATABASE_URL = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    username TEXT,
    paid INTEGER DEFAULT 0,
    invite_sent INTEGER DEFAULT 0,
    invite_link TEXT,
    expires_at BIGINT
)
""")

# ---------- BOT ----------
tg_app = Application.builder().token(TOKEN).build()

# ---------- /START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id
    username = update.effective_user.username or "none"

    cursor.execute("""
        INSERT INTO users (telegram_id, username)
        VALUES (%s, %s)
        ON CONFLICT (telegram_id) DO NOTHING
    """, (tid, username))

    keyboard = [
        [InlineKeyboardButton("🔥 Unlock My VIP 🔥", url=GUMROAD_LINK)]
    ]

    await update.message.reply_text(
        f"Hey you… 😈\n\n"
        f"💋 Exclusive +18 content\n"
        f"💦 Private videos\n"
        f"🔥 VIP-only surprises\n\n"
        f"🆔 Your ID: {tid}\n"
        f"(Paste this at checkout)\n\n"
        f"After payment, come back and type /vip 💕",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- /VIP ----------
async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id
    now = int(datetime.now(timezone.utc).timestamp())

    cursor.execute("""
        SELECT paid, invite_sent, invite_link, expires_at
        FROM users
        WHERE telegram_id=%s
    """, (tid,))
    row = cursor.fetchone()

    if not row or row[0] != 1:
        keyboard = [[InlineKeyboardButton("💳 Unlock Access", url=GUMROAD_LINK)]]
        await update.message.reply_text(
            "😈 You don’t have access yet...",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    paid, invite_sent, invite_link, expires_at = row

    # Expired
    if expires_at and expires_at < now:
        await update.message.reply_text("⏰ Your access has expired. Use /start to renew.")
        return

    # Already has invite
    if invite_sent == 1 and invite_link:
        await update.message.reply_text(f"😈 Here’s your access:\n\n{invite_link}")
        return

    # Create invite
    invite = await context.bot.create_chat_invite_link(
        chat_id=VIP_GROUP_ID,
        member_limit=1,
        expire_date=expires_at
    )

    cursor.execute("""
        UPDATE users
        SET invite_sent=1, invite_link=%s
        WHERE telegram_id=%s
    """, (invite.invite_link, tid))

    await update.message.reply_text(
        f"🔥 Your private access:\n\n{invite.invite_link}"
    )

# ---------- /STATUS ----------
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id
    now = int(datetime.now(timezone.utc).timestamp())

    cursor.execute("""
        SELECT paid, expires_at
        FROM users
        WHERE telegram_id=%s
    """, (tid,))
    row = cursor.fetchone()

    if not row or row[0] != 1:
        await update.message.reply_text("❌ No active subscription.")
        return

    paid, expires_at = row

    if expires_at and expires_at < now:
        expire_str = datetime.utcfromtimestamp(expires_at).strftime("%d/%m/%Y")
        await update.message.reply_text(f"⛔ Expired on {expire_str}")
        return

    expire_str = (
        datetime.utcfromtimestamp(expires_at).strftime("%d/%m/%Y")
        if expires_at else "Lifetime"
    )

    await update.message.reply_text(
        f"✅ Active\n📅 Valid until: {expire_str}"
    )

# ---------- HANDLERS ----------
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("vip", vip))
tg_app.add_handler(CommandHandler("status", status))

# ---------- TELEGRAM WEBHOOK ----------
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), tg_app.bot)
    asyncio.run(tg_app.process_update(update))
    return "ok"

# ---------- GUMROAD WEBHOOK ----------
@app.route("/webhook", methods=["POST"])
def gumroad_webhook():
    data = request.form.to_dict()

    telegram_id = data.get("custom_fields[Telegram ID]")
    if not telegram_id:
        return "missing telegram id", 400

    expires_at = int(
        (datetime.now(timezone.utc) + timedelta(days=1)).timestamp()
    )

    cursor.execute("""
        UPDATE users
        SET paid=1,
            expires_at=%s,
            invite_sent=0,
            invite_link=NULL
        WHERE telegram_id=%s
    """, (expires_at, int(telegram_id)))

    return "ok"

# ---------- CRON REMOVE ----------
@app.route("/cron-remove")
def cron_remove():
    now = int(datetime.now(timezone.utc).timestamp())

    cursor.execute("""
        SELECT telegram_id
        FROM users
        WHERE paid=1 AND expires_at IS NOT NULL AND expires_at < %s
    """, (now,))
    expired_users = cursor.fetchall()

    async def remove():
        for (telegram_id,) in expired_users:
            try:
                await tg_app.bot.ban_chat_member(VIP_GROUP_ID, telegram_id)
                await tg_app.bot.unban_chat_member(VIP_GROUP_ID, telegram_id)

                cursor.execute("""
                    UPDATE users
                    SET paid=0, invite_sent=0, invite_link=NULL
                    WHERE telegram_id=%s
                """, (telegram_id,))
            except Exception as e:
                print(e)

    asyncio.run(remove())
    return "ok", 200

# ---------- HOME ----------
@app.route("/")
def home():
    return "Bot online", 200

# ---------- RUN ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
