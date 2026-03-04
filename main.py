import os
import stripe
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from bot import tg_app
from database import create_table, get_connection

TOKEN = os.environ.get("BOT_TOKEN")
GROUP_ID = int(os.environ.get("GROUP_ID"))
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
CRON_SECRET = os.environ.get("CRON_SECRET")

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

app = FastAPI()

# -------- STARTUP --------

@app.on_event("startup")
async def startup():
    create_table()
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.bot.set_webhook(
        f"https://telegram-bot-ncgp.onrender.com/{TOKEN}"
    )

# -------- TELEGRAM WEBHOOK --------

@app.post("/{token}")
async def telegram_webhook(token: str, request: Request):
    if token != TOKEN:
        raise HTTPException(status_code=403)

    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}

# -------- STRIPE WEBHOOK --------

@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, STRIPE_WEBHOOK_SECRET
        )
    except Exception:
        raise HTTPException(status_code=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        telegram_id = session["metadata"]["telegram_id"]
        subscription_id = session["subscription"]

        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE subscribers
                SET status='active',
                    stripe_subscription_id=%s
                WHERE telegram_id=%s
            """, (subscription_id, telegram_id))
            conn.commit()
        conn.close()

        invite_link = await tg_app.bot.create_chat_invite_link(
            chat_id=GROUP_ID,
            member_limit=1
        )

        await tg_app.bot.send_message(
            chat_id=int(telegram_id),
            text=f"Payment confirmed ✅\n{invite_link.invite_link}"
        )

    if event["type"] in ["customer.subscription.deleted", "invoice.payment_failed"]:
        subscription_id = event["data"]["object"].get("subscription") \
            or event["data"]["object"]["id"]

        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT telegram_id
                FROM subscribers
                WHERE stripe_subscription_id=%s
            """, (subscription_id,))
            result = cur.fetchone()

            cur.execute("""
                UPDATE subscribers
                SET status='inactive'
                WHERE stripe_subscription_id=%s
            """, (subscription_id,))
            conn.commit()
        conn.close()

        if result:
            telegram_id = result["telegram_id"]

            await tg_app.bot.ban_chat_member(
                chat_id=GROUP_ID,
                user_id=int(telegram_id)
            )

            await tg_app.bot.unban_chat_member(
                chat_id=GROUP_ID,
                user_id=int(telegram_id)
            )

    return {"success": True}

# -------- CRON --------

@app.get("/cron/check_subscriptions")
async def cron(secret: str):
    if secret != CRON_SECRET:
        raise HTTPException(status_code=403)

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT telegram_id, stripe_subscription_id
            FROM subscribers
            WHERE status='active'
        """)
        subs = cur.fetchall()
    conn.close()

    for sub in subs:
        subscription = stripe.Subscription.retrieve(sub["stripe_subscription_id"])

        if subscription.status != "active":
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE subscribers
                    SET status='inactive'
                    WHERE stripe_subscription_id=%s
                """, (sub["stripe_subscription_id"],))
                conn.commit()
            conn.close()

            await tg_app.bot.ban_chat_member(
                chat_id=GROUP_ID,
                user_id=int(sub["telegram_id"])
            )

            await tg_app.bot.unban_chat_member(
                chat_id=GROUP_ID,
                user_id=int(sub["telegram_id"])
            )

    return {"status": "ok"}

# -------- HOME --------

@app.get("/")
def home():
    return {"status": "Bot online"}