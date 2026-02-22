import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Pega o token do bot da variável de ambiente
TOKEN = os.environ.get("BOT_TOKEN")

# Link do seu conteúdo
FANSLY_FEET_LINK = "https://fansly.com/Viniz_"

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🦶 Enter My Feet World 🦶", url=FANSLY_FEET_LINK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Hey you… 😈\n\n"
        "So you like feet? 🦶🔥\n\n"
        "I have something very special waiting for you there…\n\n"
        "Exclusive content\n"
        "Custom requests 💦\n\n"
        "Tap below and enjoy…",
        reply_markup=reply_markup
    )

# Comando /feet
async def feet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🦶 Enter My Feet World 🦶", url=FANSLY_FEET_LINK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "You’re back for more? 😈🦶\n\n"
        "Click below and step into my private world… 💋",
        reply_markup=reply_markup
    )

def main():
    # Cria o bot
    app = ApplicationBuilder().token(TOKEN).build()

    # Adiciona handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("feet", feet))

    # Configuração do webhook para Render
    PORT = int(os.environ.get("PORT", 10000))  # Porta que o Render fornece
    RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")  # URL pública do Render

    if not TOKEN or not RENDER_EXTERNAL_URL:
        print("Erro: variável BOT_TOKEN ou RENDER_EXTERNAL_URL não definida")
        return

    print("Bot rodando em Webhook mode...")

    # Roda o webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{RENDER_EXTERNAL_URL}/{TOKEN}"
    )

if __name__ == "__main__":
    main()