import os
import asyncio
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

async def main():
    if not TOKEN or not os.environ.get("RENDER_EXTERNAL_URL"):
        print("Erro: variável BOT_TOKEN ou RENDER_EXTERNAL_URL não definida")
        return

    PORT = int(os.environ.get("PORT", 10000))
    RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

    # Cria o bot
    app = ApplicationBuilder().token(TOKEN).build()

    # Adiciona handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("feet", feet))

    print("Bot rodando em Webhook mode...")

    # Start do bot
    await app.start()  # inicializa conexões
    await app.bot.set_webhook(f"{RENDER_EXTERNAL_URL}/{TOKEN}")  # define webhook

    # Mantém o bot rodando
    await app.updater.start_polling()  # ou await app.updater.start_webhook(...) se quiser
    await app.updater.idle()  # mantém o bot ativo

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())