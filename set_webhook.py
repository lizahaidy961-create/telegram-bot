import asyncio
from telegram import Bot

TOKEN = "8533380179:AAFtg4S8UKwx-lLGs8xS8SxjdVo_4cfp6oE"
WEBHOOK_URL = "https://telegram-bot-nt45.onrender.com/8533380179:AAFtg4S8UKwx-lLGs8xS8SxjdVo_4cfp6oE"


async def main():
    bot = Bot(token=TOKEN)
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook configurado com sucesso!")

asyncio.run(main())
