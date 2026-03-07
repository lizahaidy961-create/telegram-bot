import os
import stripe
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from database import get_connection

TOKEN = os.environ.get("BOT_TOKEN")
GROUP_ID = int(os.environ.get("GROUP_ID"))
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

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

    # -------- BLOQUEAR DUPLA ASSINATURA --------
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM subscribers WHERE telegram_id=%s",
            (user_id,)
        )
        result = cur.fetchone()
    conn.close()

    if result and result["status"] in ["active", "pending"]:
        await query.edit_message_text(
            "✅ You already have an active or pending subscription."
        )
        return

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

# -------- ADMIN --------

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized")
        return

    conn = get_connection()

    with conn.cursor() as cur:

        cur.execute("SELECT COUNT(*) FROM subscribers")
        total = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) FROM subscribers WHERE status='active'")
        active = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) FROM subscribers WHERE status='pending'")
        pending = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) FROM subscribers WHERE status='inactive'")
        inactive = cur.fetchone()["count"]

        cur.execute("""
        SELECT COUNT(*) FROM subscribers
        WHERE created_at >= CURRENT_DATE
        """)
        new_today = cur.fetchone()["count"]

        cur.execute("""
        SELECT COUNT(*) FROM subscribers
        WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
        """)
        new_week = cur.fetchone()["count"]

    conn.close()

    await update.message.reply_text(f"""
📊 BOT DASHBOARD

Users
Total: {total}
Active: {active}
Pending: {pending}
Inactive: {inactive}

Growth
New today: {new_today}
New this week: {new_week}
""")

async def getlink(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id
    today = datetime.utcnow().date()

    conn = get_connection()

    with conn.cursor() as cur:

        cur.execute("""
            SELECT status, link_count, last_link_date
            FROM subscribers
            WHERE telegram_id=%s
        """, (user_id,))

        result = cur.fetchone()

        if not result or result["status"] != "active":
            conn.close()
            await update.message.reply_text("❌ No active subscription.")
            return

        link_count = result["link_count"] or 0
        last_date = result["last_link_date"]

        # reset contador se mudou o dia
        if last_date != today:
            link_count = 0

        if link_count >= 3:
            conn.close()
            await update.message.reply_text(
                "⚠️ Daily limit reached (3 links per day)."
            )
            return

    # verificar se já está no grupo
    try:
        member = await context.bot.get_chat_member(GROUP_ID, user_id)

        if member.status in ["member", "administrator", "creator"]:
            conn.close()
            await update.message.reply_text(
                "✅ You are already inside the group."
            )
            return

    except:
        pass

    expire = datetime.utcnow() + timedelta(minutes=10)

    invite_link = await context.bot.create_chat_invite_link(
    chat_id=GROUP_ID,
    member_limit=1,
    expire_date=expire
    )

    with conn.cursor() as cur:

        cur.execute("""
            UPDATE subscribers
            SET link_count=%s,
                last_link_date=%s
            WHERE telegram_id=%s
        """, (link_count + 1, today, user_id))

        conn.commit()

    conn.close()

    await update.message.reply_text(
        f"🔑 Your access link:\n{invite_link.invite_link}"
    )

# -------- REGISTER --------

tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("subscribe", subscribe))
tg_app.add_handler(CommandHandler("status", status))
tg_app.add_handler(CommandHandler("getlink", getlink))
tg_app.add_handler(CallbackQueryHandler(subscribe_callback, pattern="^sub_"))
tg_app.add_handler(CommandHandler("admin", admin))