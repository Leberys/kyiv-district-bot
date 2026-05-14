from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask
import asyncio
import threading
import os

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Залишити звернення")],
        [KeyboardButton(text="📋 Мої звернення"), KeyboardButton(text="☎️ Корисні контакти")],
        [KeyboardButton(text="ℹ️ Про бот")]
    ],
    resize_keyboard=True
)


@app.route("/")
def home():
    return "Bot is running"


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привіт 👋\n\n"
        "Це бот району Києва.\n"
        "Тут ти можеш залишити скаргу, пропозицію або повідомити про проблему.",
        reply_markup=main_menu
    )


@dp.message(F.text == "📝 Залишити звернення")
async def create_report(message: Message):
    await message.answer(
        "Добре. Почнемо створення звернення 📝\n\n"
        "Напиши, будь ласка, коротко, що сталося або яку пропозицію хочеш залишити."
    )


@dp.message(F.text == "📋 Мої звернення")
async def my_reports(message: Message):
    await message.answer(
        "Тут буде список твоїх звернень.\n"
        "Поки ми ще підключаємо базу даних."
    )


@dp.message(F.text == "☎️ Корисні контакти")
async def contacts(message: Message):
    await message.answer(
        "Корисні контакти:\n\n"
        "КМДА: 1551\n"
        "Поліція: 102\n"
        "Швидка: 103\n"
        "ДСНС: 101"
    )


@dp.message(F.text == "ℹ️ Про бот")
async def about(message: Message):
    await message.answer(
        "Цей бот створений для збору звернень жителів районів Києва.\n\n"
        "Через нього можна залишити скаргу, пропозицію або повідомити про проблему."
    )


@dp.message()
async def fallback(message: Message):
    await message.answer(
        "Я тебе почув 👌\n\n"
        "Скористайся кнопками в меню нижче.",
        reply_markup=main_menu
    )


async def start_bot():
    await dp.start_polling(bot, handle_signals=False)


def run_bot():
    asyncio.run(start_bot())


threading.Thread(target=run_bot).start()

port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)
