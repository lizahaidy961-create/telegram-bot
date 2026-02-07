import asyncio
from telegram import Bot

TOKEN = "8533380179:AAEp0BVRQEzu0ygg0dUMOLQNFKlWZ51DofM"
WEBHOOK_URL = "https://telegram-bot-nt45.onrender.com/8533380179:AAEp0BVRQEzu0ygg0dUMOLQNFKlWZ51DofM"


async def main():
    bot = Bot(token=TOKEN)
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook configurado com sucesso!")

asyncio.run(main())
