import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ.get("8533380179:AAGm4C9zN_J1_C3SeMiUPr-iCv-pj3gAXhI")

FANSLY_FEET_LINK = "https://fansly.com/Viniz_"

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
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("feet", feet))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()