import psycopg2
import asyncio
import os
import logging
import threading
from datetime import datetime, timedelta, timezone
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------- CONFIG ----------
TOKEN = "8533380179:AAGm4C9zN_J1_C3SeMiUPr-iCv-pj3gAXhI"
VIP_GROUP_ID = -1003723951596
GUMROAD_LINK = "https://helenavargas01.gumroad.com/l/helenavargasvip"

# ---------- FLASK ----------
app = Flask(__name__)


# IDs reais que você obteve
EXPECTED_PRODUCT_ID = os.environ.get("EXPECTED_PRODUCT_ID")
EXPECTED_SELLER_ID = os.environ.get("EXPECTED_SELLER_ID")



# ---------- DATABASE ----------
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

cursor.execute("""
CREATE TABLE IF NOT EXISTS sales (
    sale_id TEXT PRIMARY KEY
)
""")


# ---------- TEXT ----------
TEXT = {
    "welcome": (
        "👋 Hello Welcome!\n\n"
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
        """
        INSERT INTO users (telegram_id, username)
        VALUES (%s, %s)
        ON CONFLICT (telegram_id) DO NOTHING
        """,
        (tid, username)
    )

    conn.commit()


    keyboard = [
        [InlineKeyboardButton("🔥 Unlock My VIP 🔥", url=GUMROAD_LINK)]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Hey you… 😈\n\n"
        f"Ready to see what I don't post anywhere else?\n\n"
        f"💋 Exclusive +18 content\n"
        f"💦 Private videos\n"
        f"🔥 VIP-only surprises\n\n"
        f"🆔 Your ID: {tid}\n"
        f"(Paste this at checkout)\n\n"
        f"After payment, come back and type /vip to enter my private world… 💕",
        reply_markup=reply_markup
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

    # User hasn't paid or doesn't exist
    if not row or row[0] != 1:
        keyboard = [
            [InlineKeyboardButton("💳 Unlock Access", url=GUMROAD_LINK)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "😈 You don’t have access yet...\n\n"
            "Tap below to unlock my private VIP content 🔥",
            reply_markup=reply_markup
        )
        return

    paid, invite_sent, invite_link, expires_at = row

    # Access expired
    if expires_at is not None and expires_at < now:
        await update.message.reply_text(
            "⏰ Your access has expired.\n\nUse /start to renew 🔥"
        )
        return

    # Already has link → resend the same
    if invite_sent == 1 and invite_link:
        await update.message.reply_text(
            f"😈 Welcome back...\n\n"
            f"Here’s your private access:\n\n{invite_link}"
        )
        return

    # Create a unique invite link
    invite = await context.bot.create_chat_invite_link(
        chat_id=VIP_GROUP_ID,
        member_limit=1,
        expire_date=expires_at
    )

    # Save in database
    cursor.execute("""
    UPDATE users
    SET invite_sent=1,
        invite_link=%s
    WHERE telegram_id=%s
""", (invite.invite_link, tid))

    conn.commit()

    await update.message.reply_text(
        f"Good choice… 😈🔥\n\n"
        f"Your private access is ready:\n\n"
        f"{invite.invite_link}\n\n"
        f"Don’t keep me waiting… 💋"
    )


# ---------- /STATUS ----------
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id
    now = datetime.now(timezone.utc).timestamp()


    cursor.execute("""
    SELECT paid, expires_at
    FROM users
    WHERE telegram_id=%s

    """, (tid,))
    row = cursor.fetchone()

    if not row or row[0] != 1:
        await update.message.reply_text("❌ You do not have an active subscription.")
        return

    paid, expires_at = row

    if expires_at is not None and expires_at < now:
        expired_date = datetime.utcfromtimestamp(expires_at).strftime("%d/%m/%Y")
        await update.message.reply_text(f"⛔ Your access expired on {expired_date}.\nUse /start to renew.")
        return

    if expires_at is not None:
        expire_str = datetime.utcfromtimestamp(expires_at).strftime("%d/%m/%Y")
    else:
        expire_str = "Lifetime"

    await update.message.reply_text(
        f"📊 Your subscription status:\n\n"
        f"✅ Payment: confirmed\n"
        f"📅 Valid until: {expire_str}\n"
        f"🔓 Access: active"
    )

# ---------- /ID ----------
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(
        f"📌 Chat ID:\n{chat.id}\n\nType: {chat.type}"
    )

# ---------- HANDLERS ----------
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("vip", vip))
tg_app.add_handler(CommandHandler("status", status))
tg_app.add_handler(CommandHandler("id", get_id))


# ---------- AUTO REMOVE EXPIRED USERS ----------
async def check_expired(context: ContextTypes.DEFAULT_TYPE):
    now = int(datetime.now(timezone.utc).timestamp())

    cursor.execute("""
        SELECT telegram_id
        FROM users
        WHERE paid=1
        AND expires_at IS NOT NULL
        AND expires_at < %s
    """, (now,))

    expired_users = cursor.fetchall()

    for (telegram_id,) in expired_users:
        try:
            await context.bot.ban_chat_member(VIP_GROUP_ID, telegram_id)
            await context.bot.unban_chat_member(VIP_GROUP_ID, telegram_id)

            cursor.execute("""
                UPDATE users
                SET paid=0,
                invite_sent=0,
                invite_link=NULL,
                expires_at=NULL

                WHERE telegram_id=%s
            """, (telegram_id,))

            print(f"Removed expired user: {telegram_id}")

        except Exception as e:
            print("Error removing user:", e)


# ---------- EVENT LOOP (THREAD SEPARADA) ----------
loop = asyncio.new_event_loop()

def run_bot():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(tg_app.initialize())
    loop.run_until_complete(tg_app.start())
   
    tg_app.job_queue.run_repeating(
        check_expired,
        interval=3600,   # 1 hora
        first=30         # começa 30 segundos após iniciar
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
    return "ok"

# ---------- GUMROAD WEBHOOK ----------
logging.basicConfig(level=logging.INFO)

@app.route("/webhook", methods=["POST"])
def gumroad_webhook():
    data = request.form.to_dict()
    logging.info("Gumroad: %s", data)

    # 1️⃣ Validar evento
    if data.get("event") != "sale":
        return "ignored event", 200

    # 2️⃣ Validar product_id
    if data.get("product_id") != EXPECTED_PRODUCT_ID:
        return "invalid product", 403

    # 3️⃣ Validar seller_id
    if data.get("seller_id") != EXPECTED_SELLER_ID:
        return "invalid seller", 403

    # 4️⃣ Bloquear testes
    if data.get("test") == "true":
        return "test ignored", 200

    telegram_id = data.get("custom_fields[Telegram ID]")
    if not telegram_id:
        return "missing telegram id", 400

    sale_id = data.get("sale_id")
    if not sale_id:
        return "missing sale_id", 400

    # 5️⃣ Anti-replay
    cursor.execute("SELECT 1 FROM sales WHERE sale_id=%s", (sale_id,))
    if cursor.fetchone():
        return "already processed", 200

    # Expiração 30 dias
    expires_at = int(
        (datetime.now(timezone.utc) + timedelta(days=30)).timestamp()
    )

    cursor.execute("""
        UPDATE users
        SET paid=1,
            expires_at=%s,
            invite_sent=0,
            invite_link=NULL
        WHERE telegram_id=%s
    """, (expires_at, int(telegram_id)))

    cursor.execute("""
        INSERT INTO sales (sale_id)
        VALUES (%s)
    """, (sale_id,))

    return "ok"


# ---------- RUN FLASK ----------
@app.route("/")
def home():
    return "Bot online", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)