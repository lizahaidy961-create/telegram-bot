import asyncio
import os
import threading
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import stripe
from datetime import datetime, timedelta 

# ---------- CONFIG ----------
TOKEN = os.environ.get("BOT_TOKEN")
GROUP_ID = int(os.environ.get("GROUP_ID"))

# Stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

# Database
DATABASE_URL = os.environ.get("DATABASE_URL")
def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# ---------- CREATE TABLE ----------
def create_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT UNIQUE,
            status TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

create_table()

# ---------- FLASK ----------
app = Flask(__name__)

# ---------- BOT ----------
tg_app = Application.builder().token(TOKEN).build()

# ---------- MESSAGES ----------
async def start_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message for /start"""
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "To get access, you need to subscribe first.\n"
        "Type /subscribe to choose your subscription plan and get access."
    )

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    await update.message.reply_text(f"📌 Chat ID:\n\nID: {chat_id}\nType: {chat_type}")

# ---------- SUBSCRIBE COMMAND ----------
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("7 Days", callback_data="sub_7"),
            InlineKeyboardButton("30 Days", callback_data="sub_30")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Choose your subscription plan to get access:",
        reply_markup=reply_markup
    )

# ---------- SUBSCRIBE CALLBACK ----------
async def subscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Map plan to Stripe price IDs
    price_map = {
    "sub_7": os.environ.get("PRICE_ID_7"),
    "sub_30": os.environ.get("PRICE_ID_30")
}
    price_id = price_map.get(query.data)
    if not price_id:
        await query.edit_message_text("Invalid plan.")
        return

    # Check if user already has an active subscription
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM subscribers WHERE telegram_id=%s", (user_id,))
        existing = cur.fetchone()
    conn.close()
    if existing and existing['status'] == 'active':
        await query.edit_message_text("You already have an active subscription ✅")
        return

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url="https://t.me/helenavarga_bot",
            cancel_url="https://t.me/helenavarga_bot",
            metadata={"telegram_id": str(user_id)}
        )

        # Save subscription as pending
        customer_id = session["customer"]
        subscription_id = session.get("subscription")
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO subscribers (telegram_id, stripe_customer_id, stripe_subscription_id, status)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (telegram_id) DO UPDATE
                SET stripe_customer_id = EXCLUDED.stripe_customer_id,
                    stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                    status = 'pending'
            """, (user_id, customer_id, subscription_id, 'pending'))
            conn.commit()
        conn.close()

        await query.edit_message_text(f"💳 Click the link below to pay and unlock access:\n{session.url}")
    except Exception as e:
        await query.edit_message_text(f"Error creating checkout session: {e}")

# ---------- STATUS COMMAND ----------
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM subscribers WHERE telegram_id=%s", (user_id,))
        result = cur.fetchone()
    conn.close()
    if result:
        await update.message.reply_text(f"Your subscription status: {result['status']}")
    else:
        await update.message.reply_text("You have no subscription. Type /subscribe to start one.")


   # ---------- GETLINK COMMAND ----------
from datetime import datetime, timedelta

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM subscribers WHERE telegram_id=%s",
            (user_id,)
        )
        result = cur.fetchone()
    conn.close()

    if not result or result["status"] != "active":
        await update.message.reply_text(
            "❌ You don't have an active subscription."
        )
        return

    try:
        expire_date = datetime.utcnow() + timedelta(minutes=10)

        invite_link = await tg_app.bot.create_chat_invite_link(
            chat_id=GROUP_ID,
            member_limit=1,
            expire_date=expire_date
        )

        await update.message.reply_text(
            f"✅ Here is your private access link:\n{invite_link.invite_link}"
        )

    except Exception as e:
        await update.message.reply_text(
            "⚠️ Error generating link. Please contact support."
        )
        print("Invite link error:", e)

# ---------- REGISTER HANDLERS ----------
tg_app.add_handler(CommandHandler("start", start_message))
tg_app.add_handler(CommandHandler("id", get_chat_id))
tg_app.add_handler(CommandHandler("subscribe", subscribe))
tg_app.add_handler(CommandHandler("status", status))
tg_app.add_handler(CallbackQueryHandler(subscribe_callback, pattern="^sub_"))
tg_app.add_handler(CommandHandler("getlink", get_link))

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

# Start bot thread when module loads (Gunicorn worker)
threading.Thread(target=run_bot, daemon=True).start()
# ---------- TELEGRAM WEBHOOK ----------
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), tg_app.bot)
    asyncio.run_coroutine_threadsafe(tg_app.process_update(update), loop)
    return "ok", 200

# ---------- STRIPE WEBHOOK ----------
@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError:
        return "Invalid signature", 400

    # ---------------- CHECKOUT COMPLETED ----------------
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        telegram_id = session.get("metadata", {}).get("telegram_id")
        subscription_id = session.get("subscription")

        if not subscription_id:
            session_full = stripe.checkout.Session.retrieve(
                session["id"], expand=["subscription"]
            )
            subscription_id = session_full["subscription"]["id"]

        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE subscribers
                SET status='active', stripe_subscription_id=%s
                WHERE telegram_id=%s
            """, (subscription_id, telegram_id))
            conn.commit()
        conn.close()

        if telegram_id:
            invite_link = asyncio.run_coroutine_threadsafe(
                tg_app.bot.create_chat_invite_link(
                    chat_id=GROUP_ID, member_limit=1
                ),
                loop
            ).result()

            asyncio.run_coroutine_threadsafe(
                tg_app.bot.send_message(
                    chat_id=int(telegram_id),
                    text=f"Payment confirmed ✅\nHere is your access link:\n{invite_link.invite_link}"
                ),
                loop
            )

    # ---------------- SUBSCRIPTION CANCELED ----------------
    if event["type"] == "customer.subscription.deleted":
        subscription_id = event["data"]["object"]["id"]

        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT telegram_id FROM subscribers WHERE stripe_subscription_id=%s",
                (subscription_id,)
            )
            result = cur.fetchone()

            # ✅ Atualiza status
            cur.execute(
                "UPDATE subscribers SET status='inactive' WHERE stripe_subscription_id=%s",
                (subscription_id,)
            )
            conn.commit()
        conn.close()

        if result:
            telegram_id = result["telegram_id"]

            asyncio.run_coroutine_threadsafe(
                tg_app.bot.ban_chat_member(
                    chat_id=GROUP_ID,
                    user_id=int(telegram_id)
                ),
                loop
            ).result()

            asyncio.run_coroutine_threadsafe(
                tg_app.bot.unban_chat_member(
                    chat_id=GROUP_ID,
                    user_id=int(telegram_id)
                ),
                loop
            ).result()

    # ---------------- PAYMENT FAILED ----------------
    if event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        subscription_id = invoice.get("subscription")

        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT telegram_id FROM subscribers WHERE stripe_subscription_id=%s",
                (subscription_id,)
            )
            result = cur.fetchone()

            # ✅ Atualiza status
            cur.execute(
                "UPDATE subscribers SET status='inactive' WHERE stripe_subscription_id=%s",
                (subscription_id,)
            )
            conn.commit()
        conn.close()

        if result:
            telegram_id = result["telegram_id"]

            asyncio.run_coroutine_threadsafe(
                tg_app.bot.ban_chat_member(
                    chat_id=GROUP_ID,
                    user_id=int(telegram_id)
                ),
                loop
            ).result()

            asyncio.run_coroutine_threadsafe(
                tg_app.bot.unban_chat_member(
                    chat_id=GROUP_ID,
                    user_id=int(telegram_id)
                ),
                loop
            ).result()

    return jsonify({"status": "success"}), 200


@app.route("/cron/check_subscriptions", methods=["GET"])
def cron_check_subscriptions():
    secret = request.args.get("secret")

    if secret != os.environ.get("CRON_SECRET"):
        return "Unauthorized", 403

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT telegram_id, stripe_subscription_id FROM subscribers WHERE status='active'")
        active_subs = cur.fetchall()
    conn.close()

    for sub in active_subs:
        telegram_id = sub['telegram_id']
        subscription_id = sub['stripe_subscription_id']

        try:
            subscription = stripe.Subscription.retrieve(subscription_id)

            if subscription.status != "active":
                conn = get_connection()
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE subscribers SET status='inactive' WHERE stripe_subscription_id=%s",
                        (subscription_id,)
                    )
                    conn.commit()
                conn.close()

                asyncio.run_coroutine_threadsafe(
                    tg_app.bot.ban_chat_member(chat_id=GROUP_ID, user_id=int(telegram_id)), loop
                ).result()

                asyncio.run_coroutine_threadsafe(
                    tg_app.bot.unban_chat_member(chat_id=GROUP_ID, user_id=int(telegram_id)), loop
                ).result()

        except Exception:
            print(f"Erro ao verificar assinatura {subscription_id}")

    return "OK", 200


# ---------- HOME ----------
@app.route("/")
def home():
    return "Bot online", 200
