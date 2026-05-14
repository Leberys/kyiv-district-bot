from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from flask import Flask
import asyncio
import threading
import os

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привіт 👋\n\n"
        "Це бот району Києва.\n"
        "Тут ти можеш залишити скаргу, пропозицію або повідомити про проблему."
    )

@dp.message()
async def echo(message: Message):
    await message.answer(f"Отримано:\n\n{message.text}")

async def start_bot():
    await dp.start_polling(bot, handle_signals=False)

def run_bot():
    asyncio.run(start_bot())

threading.Thread(target=run_bot).start()

port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)
