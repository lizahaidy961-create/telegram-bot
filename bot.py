from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import sqlite3
import datetime

# ================= CONFIG =================
TOKEN = "8533380179:AAEp0BVRQEzu0ygg0dUMOLQNFKlWZ51DofM"
VIP_GROUP_ID = -3616377094
REDIRECT_LINK = "https://redirecionamento-iota.vercel.app"
# ==========================================

bot = Bot(token=TOKEN)
app = Flask(__name__)

# -------- Banco de Dados (SQLite) --------
def db_connection():
    return sqlite3.connect("database.db", check_same_thread=False)

conn = db_connection()
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    email TEXT,
    language TEXT,
    paid INTEGER DEFAULT 0
)
""")
conn.commit()

# -------- Textos PT / EN --------
TEXT = {
    "pt": {
        "welcome": "👋 Bem-vindo!\nDigite o e-mail que você usará no pagamento:",
        "link": "💳 Finalize sua compra aqui:\n{}\n\n⚠️ Use o MESMO e-mail informado.",
        "success": "🎉 Pagamento confirmado!\nAqui está seu acesso ao grupo VIP:\n{}"
    },
    "en": {
        "welcome": "👋 Welcome!\nPlease type the email you will use for payment:",
        "link": "💳 Complete your purchase here:\n{}\n\n⚠️ Use the SAME email.",
        "success": "🎉 Payment confirmed!\nHere is your VIP group access:\n{}"
    }
}

# -------- Detectar idioma --------
def detect_language(update):
    return "pt" if update.effective_user.language_code == "pt-br" else "en"

# -------- /start --------
def start(update, context):
    telegram_id = update.effective_user.id
    lang = detect_language(update)

    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id, language) VALUES (?,?)",
        (telegram_id, lang)
    )
    conn.commit()

    update.message.reply_text(TEXT[lang]["welcome"])

# -------- Capturar Email --------
def get_email(update, context):
    telegram_id = update.effective_user.id
    email = update.message.text.strip()

    cursor.execute(
        "UPDATE users SET email=? WHERE telegram_id=?",
        (email, telegram_id)
    )
    conn.commit()

    lang = detect_language(update)
    update.message.reply_text(TEXT[lang]["link"].format(REDIRECT_LINK))

# -------- Dispatcher --------
dispatcher = Dispatcher(bot, None, workers=1)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, get_email))

# -------- Webhook --------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Webhook:", data)

    email = None
    status = None

    # Kiwify
    if "customer" in data:
        email = data["customer"].get("email")
        status = data.get("status")

    # Gumroad
    if data.get("event") == "sale":
        email = data["email"]
        status = "paid"

    if status != "paid" or not email:
        return "ignored"

    cursor.execute("SELECT telegram_id, language FROM users WHERE email=?", (email,))
    user = cursor.fetchone()

    if not user:
        return "user not found"

    telegram_id, lang = user

    # Criar link do grupo
    invite = bot.create_chat_invite_link(VIP_GROUP_ID, member_limit=1)

    bot.send_message(
        chat_id=telegram_id,
        text=TEXT[lang]["success"].format(invite.invite_link)
    )

    cursor.execute(
        "UPDATE users SET paid=1 WHERE telegram_id=?",
        (telegram_id,)
    )
    conn.commit()

    return "ok"

# -------- Receber updates Telegram --------
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# -------- Run --------
if __name__ == "__main__":
    app.run(port=5000)
