import os
import stripe
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from database import get_connection

TOKEN = os.environ.get("BOT_TOKEN")
GROUP_ID = int(os.environ.get("GROUP_ID"))

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

tg_app = Application.builder().token(TOKEN).build()

# -------- COMMANDS --------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\nType /subscribe to choose your plan."
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("7 Days", callback_data="sub_7"),
        InlineKeyboardButton("30 Days", callback_data="sub_30")
    ]]
    await update.message.reply_text(
        "Choose your plan:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def subscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    price_map = {
        "sub_7": os.environ.get("PRICE_ID_7"),
        "sub_30": os.environ.get("PRICE_ID_30")
    }

    price_id = price_map.get(query.data)
    if not price_id:
        await query.edit_message_text("Invalid plan.")
        return

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url="https://t.me/seu_bot",
        cancel_url="https://t.me/seu_bot",
        metadata={"telegram_id": str(user_id)}
    )

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO subscribers (telegram_id, status)
            VALUES (%s, %s)
            ON CONFLICT (telegram_id)
            DO UPDATE SET status='pending'
        """, (user_id, 'pending'))
        conn.commit()
    conn.close()

    await query.edit_message_text(f"💳 Pay here:\n{session.url}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM subscribers WHERE telegram_id=%s", (user_id,))
        result = cur.fetchone()
    conn.close()

    if result:
        await update.message.reply_text(f"Status: {result['status']}")
    else:
        await update.message.reply_text("No subscription found.")

async def getlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM subscribers WHERE telegram_id=%s", (user_id,))
        result = cur.fetchone()
    conn.close()

    if not result or result["status"] != "active":
        await update.message.reply_text("❌ No active subscription.")
        return

    expire_date = datetime.utcnow() + timedelta(minutes=10)

    invite_link = await tg_app.bot.create_chat_invite_link(
        chat_id=GROUP_ID,
        member_limit=1,
        expire_date=expire_date
    )

    await update.message.reply_text(invite_link.invite_link)

# -------- REGISTER --------

tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("subscribe", subscribe))
tg_app.add_handler(CommandHandler("status", status))
tg_app.add_handler(CommandHandler("getlink", getlink))
tg_app.add_handler(CallbackQueryHandler(subscribe_callback, pattern="^sub_"))