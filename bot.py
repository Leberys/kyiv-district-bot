from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask
import asyncio
import threading
import os
import asyncpg

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

waiting_for_report = {}

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


async def get_connection():
    return await asyncpg.connect(DATABASE_URL)


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
    waiting_for_report[message.from_user.id] = True

    await message.answer(
        "Опиши проблему або пропозицію 📝"
    )


@dp.message(F.text == "📋 Мої звернення")
async def my_reports(message: Message):
    conn = await get_connection()

    reports = await conn.fetch(
        """
        SELECT id, description, status
        FROM reports
        WHERE user_id = $1
        ORDER BY id DESC
        """,
        str(message.from_user.id)
    )

    await conn.close()

    if not reports:
        await message.answer("У тебе поки немає звернень.")
        return

    text = "📋 Твої звернення:\n\n"

    for report in reports:
        text += (
            f"№{report['id']}\n"
            f"Статус: {report['status']}\n"
            f"{report['description']}\n\n"
        )

    await message.answer(text)


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
        "Бот для звернень жителів Києва."
    )


@dp.message()
async def handle_messages(message: Message):

    if waiting_for_report.get(message.from_user.id):

        conn = await get_connection()

        await conn.execute(
            """
            INSERT INTO reports (
                user_id,
                username,
                description,
                status
            )
            VALUES ($1, $2, $3, $4)
            """,
            str(message.from_user.id),
            message.from_user.username,
            message.text,
            "Нове"
        )

        await conn.close()

        waiting_for_report.pop(message.from_user.id)

        await message.answer(
            "✅ Звернення успішно створене!"
        )

        return

    await message.answer(
        "Скористайся кнопками меню 👇",
        reply_markup=main_menu
    )


async def start_bot():
    await dp.start_polling(bot, handle_signals=False)


def run_bot():
    asyncio.run(start_bot())


threading.Thread(target=run_bot).start()

port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)
