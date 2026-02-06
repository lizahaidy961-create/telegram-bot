from telegram import Bot

TOKEN = "8533380179:AAEp0BVRQEzu0ygg0dUMOLQNFKlWZ51DofM"
WEBHOOK_URL = "https://damian-pupilless-erroneously.ngrok-free.dev/" + TOKEN

bot = Bot(token=TOKEN)
bot.set_webhook(WEBHOOK_URL)

print("Webhook configurado com sucesso!")
