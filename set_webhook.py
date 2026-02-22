import asyncio
from telegram import Bot

TOKEN = "8533380179:AAGm4C9zN_J1_C3SeMiUPr-iCv-pj3gAXhI"
WEBHOOK_URL = "https://telegram-bot-nt45.onrender.com/8533380179:AAGm4C9zN_J1_C3SeMiUPr-iCv-pj3gAXhI"


async def main():
    bot = Bot(token=TOKEN)
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook configurado com sucesso!")

asyncio.run(main())
