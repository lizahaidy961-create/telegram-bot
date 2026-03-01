import asyncio
import os
import threading
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import stripe

# ---------- CONFIG ----------
TOKEN = os.environ.get("BOT_TOKEN")
FANSLY_FEET_LINK = "https://fansly.com/Viniz_"
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
            telegram_id BIGINT,
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
async def send_feet_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("✨ Unlock My Private Feet Room ✨", url=FANSLY_FEET_LINK)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "So… you found your weakness? 🦶😈\n\n"
        "Good.\n\n"
        "Behind this button there’s a private space where I don't hold back...\n\n"
        "•🔥Slow teasing\n•💦Intimate close-ups\n•Custom experiences just for you\n\n"
        "Not everyone gets access.\nOnly the ones who dare to click.\n\nReady?",
        reply_markup=reply_markup
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
    await update.message.reply_text("Choose your subscription plan:", reply_markup=reply_markup)

# ---------- SUBSCRIBE CALLBACK ----------
async def subscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Map plan to Stripe price IDs (replace with your actual Stripe price IDs)
    price_map = {
       "sub_7": "price_1T5vMKFWiapY4wbBG3vCwaIz",   # Replace with your Stripe 7-day price ID
       "sub_30": "price_1T5vLYFWiapY4wbBj4W33Wh7"
    }
    price_id = price_map.get(query.data)
    if not price_id:
        await query.edit_message_text("Invalid plan.")
        return

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"https://t.me/{query.from_user.username}",
            cancel_url=f"https://t.me/{query.from_user.username}",
            metadata={"telegram_id": str(user_id)}
        )

        # Save subscription in DB
        customer_id = session["customer"]
        subscription_id = session["subscription"]
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO subscribers (telegram_id, stripe_customer_id, stripe_subscription_id, status)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (stripe_subscription_id) DO NOTHING
            """, (user_id, customer_id, subscription_id, 'pending'))
            conn.commit()
        conn.close()

        await query.edit_message_text(f"💳 Click the link below to pay and unlock access:\n{session.url}")
    except Exception as e:
        await query.edit_message_text(f"Error creating checkout session: {e}")

# ---------- REGISTER HANDLERS ----------
tg_app.add_handler(CommandHandler("start", send_feet_link))
tg_app.add_handler(CommandHandler("feet", send_feet_link))
tg_app.add_handler(CommandHandler("id", get_chat_id))
tg_app.add_handler(CommandHandler("subscribe", subscribe))
tg_app.add_handler(CallbackQueryHandler(subscribe_callback, pattern="^sub_"))

# ---------- EVENT LOOP ----------
loop = asyncio.new_event_loop()
def run_bot():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(tg_app.initialize())
    loop.run_until_complete(tg_app.start())
    loop.run_until_complete(tg_app.bot.set_webhook(f"https://telegram-bot-ncgp.onrender.com/{TOKEN}"))
    loop.run_forever()
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
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError:
        return "Invalid signature", 400

    # CHECKOUT COMPLETED
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        telegram_id = session.get("metadata", {}).get("telegram_id")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        # Update DB status
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE subscribers SET status='active'
                WHERE stripe_subscription_id=%s
            """, (subscription_id,))
            conn.commit()
        conn.close()

        if telegram_id:
            invite_link = asyncio.run_coroutine_threadsafe(
                tg_app.bot.create_chat_invite_link(chat_id=GROUP_ID, member_limit=1), loop
            ).result()
            asyncio.run_coroutine_threadsafe(
                tg_app.bot.send_message(chat_id=int(telegram_id),
                                        text=f"Payment confirmed ✅\nHere is your access link:\n{invite_link.invite_link}"),
                loop
            )

    # SUBSCRIPTION CANCELED
    if event["type"] == "customer.subscription.deleted":
        subscription_id = event["data"]["object"]["id"]
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT telegram_id FROM subscribers WHERE stripe_subscription_id=%s", (subscription_id,))
            result = cur.fetchone()
        conn.close()

        if result:
            telegram_id = result['telegram_id']
            asyncio.run_coroutine_threadsafe(
                tg_app.bot.ban_chat_member(chat_id=GROUP_ID, user_id=int(telegram_id)),
                loop
            )

    return jsonify({"status": "success"}), 200

# ---------- HOME ----------
@app.route("/")
def home():
    return "Bot online", 200

# ---------- RUN FLASK ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)