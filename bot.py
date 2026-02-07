import sqlite3
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

# ---------- CONFIGURAÇÕES ----------
TOKEN = "8533380179:AAEp0BVRQEzu0ygg0dUMOLQNFKlWZ51DofM"
VIP_GROUP_ID = -3616377094
REDIRECT_LINK = "https://helenavargas01.gumroad.com/l/helenavargasvip"

app = Flask(__name__)

# ---------- BANCO DE DADOS ----------
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

# Cria tabela se não existir
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    email TEXT,
    language TEXT,
    paid INTEGER DEFAULT 0
)
""")
conn.commit()

# Adiciona coluna username se não existir
cursor.execute("PRAGMA table_info(users)")
columns = [col[1] for col in cursor.fetchall()]
if "username" not in columns:
    cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
    conn.commit()

# ---------- TEXTOS ----------
TEXT = {
    "pt": {
        "welcome": "👋 Bem-vindo!\n\nID: {id}\nUsername: {username}\nEmail: {email}\n\n💳 Compre agora: {link}",
        "success": "🎉 Pagamento confirmado!\nAqui está seu acesso ao grupo VIP:\n{link}"
    },
    "en": {
        "welcome": "👋 Welcome!\n\nID: {id}\nUsername: {username}\nEmail: {email}\n\n💳 Purchase here: {link}",
        "success": "🎉 Payment confirmed!\nHere is your VIP group access:\n{link}"
    }
}

def get_lang(update: Update):
    return "pt" if update.effective_user.language_code == "pt-br" else "en"

# ---------- HANDLER /START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    username = update.effective_user.username or "não disponível"
    lang = get_lang(update)

    # Insere ou atualiza usuário
    cursor.execute("""
        INSERT OR IGNORE INTO users (telegram_id, username, language)
        VALUES (?, ?, ?)
    """, (telegram_id, username, lang))
    conn.commit()

    # Atualiza username se necessário
    cursor.execute("UPDATE users SET username=? WHERE telegram_id=?", (username, telegram_id))
    conn.commit()

    # Pega email se já existir
    cursor.execute("SELECT email FROM users WHERE telegram_id=?", (telegram_id,))
    result = cursor.fetchone()
    email = result[0] if result and result[0] else "✉️ a definir"

    await update.message.reply_text(
        TEXT[lang]["welcome"].format(
            id=telegram_id,
            username=username,
            email=email,
            link=REDIRECT_LINK
        )
    )

# ---------- TELEGRAM APP ----------
tg_app = Application.builder().token(TOKEN).build()
tg_app.add_handler(CommandHandler("start", start))

# ---------- WEBHOOK TELEGRAM ----------
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), tg_app.bot)
    asyncio.run(tg_app.process_update(update))  # loop temporário
    return "ok"

# ---------- WEBHOOK PAGAMENTO ----------
@app.route("/webhook", methods=["POST"])
def payment_webhook():
    data = request.json
    print("Webhook recebido:", data)

    email = None

    # Kiwify
    if "customer" in data:
        email = data["customer"].get("email")
        if data.get("status") != "paid":
            return "ignored"

    # Gumroad
    if data.get("event") == "sale":
        email = data.get("email")

    if not email:
        return "ignored"

    # Procura usuário pelo email
    cursor.execute("SELECT telegram_id, language FROM users WHERE email=?", (email,))
    user = cursor.fetchone()
    if not user:
        return "user not found"

    telegram_id, lang = user

    async def send_invite():
        invite = await tg_app.bot.create_chat_invite_link(
            chat_id=VIP_GROUP_ID,
            member_limit=1
        )
        await tg_app.bot.send_message(
            chat_id=telegram_id,
            text=TEXT[lang]["success"].format(link=invite.invite_link)
        )

    asyncio.run(send_invite())

    # Marca como pago
    cursor.execute("UPDATE users SET paid=1 WHERE telegram_id=?", (telegram_id,))
    conn.commit()

    return "ok"

# ---------- RUN ----------
if __name__ == "__main__":
    # Inicializa bot de forma correta sem warnings
    asyncio.run(tg_app.initialize())
    app.run(host="0.0.0.0", port=5000)
