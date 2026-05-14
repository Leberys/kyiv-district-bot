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

user_states = {}

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Залишити звернення")],
        [KeyboardButton(text="📋 Мої звернення"), KeyboardButton(text="☎️ Корисні контакти")],
        [KeyboardButton(text="ℹ️ Про бот")]
    ],
    resize_keyboard=True
)

type_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚨 Скарга")],
        [KeyboardButton(text="💡 Пропозиція")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)

skip_address_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Пропустити адресу")]
    ],
    resize_keyboard=True
)

skip_contact_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Пропустити")]
    ],
    resize_keyboard=True
)


@app.route("/")
def home():
    return "Bot is running"


async def get_connection():
    return await asyncpg.connect(
        DATABASE_URL,
        ssl="require"
    )


@dp.message(CommandStart())
async def start(message: Message):
    user_states.pop(message.from_user.id, None)

    await message.answer(
        "Привіт 👋\n\n"
        "Це бот Деснянського району Києва.\n"
        "Тут ти можеш залишити свою пропозицію або повідомити про проблему.",
        reply_markup=main_menu
    )


@dp.message(F.text == "📝 Залишити звернення")
async def create_report(message: Message):
    user_states[message.from_user.id] = {"step": "choose_type"}

    await message.answer(
        "Оберіть тип звернення:",
        reply_markup=type_menu
    )


@dp.message(F.text == "⬅️ Назад")
async def back(message: Message):
    user_states.pop(message.from_user.id, None)

    await message.answer(
        "Повертаємось у головне меню.",
        reply_markup=main_menu
    )


@dp.message(F.text.in_(["🚨 Скарга", "💡 Пропозиція"]))
async def choose_type(message: Message):
    user_states[message.from_user.id] = {
        "step": "description",
        "category": "Скарга" if message.text == "🚨 Скарга" else "Пропозиція"
    }

    await message.answer(
        "Опиши, будь ласка, суть звернення 📝"
    )


@dp.message(F.text == "📋 Мої звернення")
async def my_reports(message: Message):
    conn = await get_connection()

    reports = await conn.fetch(
        """
        SELECT id, category, description, address, contact, status
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
            f"Тип: {report['category'] or 'Не вказано'}\n"
            f"Статус: {report['status'] or 'Нове'}\n"
            f"Опис: {report['description'] or 'Не вказано'}\n"
            f"Адреса: {report['address'] or 'Не вказано'}\n"
            f"Контакт: {report['contact'] or 'Не вказано'}\n\n"
        )

    await message.answer(text, reply_markup=main_menu)


@dp.message(F.text == "☎️ Корисні контакти")
async def contacts(message: Message):
    await message.answer(
        "Корисні контакти:\n\n"
        "КМДА: 1551\n"
        "Поліція: 102\n"
        "Швидка: 103\n"
        "ДСНС: 101",
        reply_markup=main_menu
    )


@dp.message(F.text == "ℹ️ Про бот")
async def about(message: Message):
    await message.answer(
        "Цей бот створений для звернень жителів Деснянського району Києва.\n\n"
        "Через нього можна залишити скаргу або пропозицію.",
        reply_markup=main_menu
    )


@dp.message()
async def handle_messages(message: Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if not state:
        await message.answer(
            "Скористайся кнопками меню 👇",
            reply_markup=main_menu
        )
        return

    if state["step"] == "description":
        state["description"] = message.text
        state["step"] = "address"

        await message.answer(
            "Вкажи адресу.\n\n"
            "Наприклад: вул. Оноре де Бальзака, 55\n\n"
            "Якщо адреси немає — натисни «Пропустити адресу».",
            reply_markup=skip_address_menu
        )
        return

    if state["step"] == "address":
        if message.text == "Пропустити адресу":
            state["address"] = None
        else:
            state["address"] = message.text

        state["step"] = "contact"

        await message.answer(
            "Залиш контакт для зв’язку.\n\n"
            "Це може бути номер телефону, Telegram username або будь-який інший контакт.\n\n"
            "Якщо не хочеш залишати контакт — натисни «Пропустити контакт».",
            reply_markup=skip_contact_menu
        )
        return

    if state["step"] == "contact":
        if message.text == "Пропустити контакт":
            state["contact"] = None
        else:
            state["contact"] = message.text

        conn = await get_connection()

        await conn.execute(
            """
            INSERT INTO reports (
                user_id,
                username,
                district,
                category,
                description,
                address,
                contact,
                status
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            str(user_id),
            message.from_user.username,
            "Деснянський",
            state["category"],
            state["description"],
            state["address"],
            state["contact"],
            "Нове"
        )

        await conn.close()
        user_states.pop(user_id, None)

        await message.answer(
            "✅ Звернення успішно створене!\n\n"
            "Дякуємо, що допомагаєш покращувати Деснянський район.",
            reply_markup=main_menu
        )
        return


async def start_bot():
    await dp.start_polling(bot, handle_signals=False)


def run_bot():
    asyncio.run(start_bot())


threading.Thread(target=run_bot).start()

port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)
