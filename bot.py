import asyncio
import os
import threading
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import stripe

# ---------- CONFIG ----------
TOKEN = os.environ.get("BOT_TOKEN")
FANSLY_FEET_LINK = "https://fansly.com/Viniz_"
GROUP_ID = int(os.environ.get("GROUP_ID"))

# Stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

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

# ---------- SUBSCRIBE COMMAND ----------
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": "price_XXXXXXXX",  # Substitua pelo ID do preço criado na Stripe
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"https://t.me/{update.effective_user.username}",  # ou link do bot
            cancel_url=f"https://t.me/{update.effective_user.username}",
            metadata={
                "telegram_id": str(user_id)
            }
        )

        await update.message.reply_text(
            f"💳 Assine aqui para liberar acesso:\n{checkout_session.url}"
        )
    except Exception as e:
        await update.message.reply_text(f"Erro ao criar sessão de pagamento: {e}")

# ---------- HANDLERS ----------
tg_app.add_handler(CommandHandler("start", send_feet_link))
tg_app.add_handler(CommandHandler("feet", send_feet_link))
tg_app.add_handler(CommandHandler("id", get_chat_id))
tg_app.add_handler(CommandHandler("subscribe", subscribe))

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

    # PAGAMENTO CONFIRMADO
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        telegram_id = session.get("metadata", {}).get("telegram_id")

        if telegram_id:
            invite_link = asyncio.run_coroutine_threadsafe(
                tg_app.bot.create_chat_invite_link(
                    chat_id=GROUP_ID,
                    member_limit=1
                ),
                loop
            ).result()

            asyncio.run_coroutine_threadsafe(
                tg_app.bot.send_message(
                    chat_id=int(telegram_id),
                    text=f"Pagamento confirmado ✅\n\nAqui está seu acesso:\n{invite_link.invite_link}"
                ),
                loop
            )

    # CANCELAMENTO DE ASSINATURA
    if event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        telegram_id = subscription.get("metadata", {}).get("telegram_id")

        if telegram_id:
            asyncio.run_coroutine_threadsafe(
                tg_app.bot.ban_chat_member(
                    chat_id=GROUP_ID,
                    user_id=int(telegram_id)
                ),
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