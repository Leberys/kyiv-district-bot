from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask
from dotenv import load_dotenv
import asyncio
import threading
import os
import asyncpg


load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = os.getenv("ADMIN_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

user_states = {}

@app.route("/")
def home():
    return "Bot is running"

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Залишити звернення")],
        [KeyboardButton(text="📋 Мої звернення"), KeyboardButton(text="☎️ Корисні контакти")],
        [KeyboardButton(text="ℹ️ Про бот")]
    ],
    resize_keyboard=True
)

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📥 Нові звернення")],
        [KeyboardButton(text="📚 Усі звернення")],
        [KeyboardButton(text="🔄 Змінити статус")],
        [KeyboardButton(text="⬅️ Вийти з адмінки")]
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
        [KeyboardButton(text="Пропустити контакт")]
    ],
    resize_keyboard=True
)

status_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Нове")],
        [KeyboardButton(text="В роботі")],
        [KeyboardButton(text="Виконано")],
        [KeyboardButton(text="Відхилено")],
        [KeyboardButton(text="⬅️ Назад")]
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


def is_admin(user_id: int) -> bool:
    return str(user_id) == str(ADMIN_ID)


async def send_long_message(message: Message, text: str, reply_markup=None):
    if len(text) <= 3900:
        await message.answer(text, reply_markup=reply_markup)
        return

    parts = []
    while len(text) > 3900:
        split_index = text.rfind("\n\n", 0, 3900)

        if split_index == -1:
            split_index = 3900

        parts.append(text[:split_index])
        text = text[split_index:].strip()

    if text:
        parts.append(text)

    for index, part in enumerate(parts):
        if index == len(parts) - 1:
            await message.answer(part, reply_markup=reply_markup)
        else:
            await message.answer(part)


async def show_reports(message: Message, only_new: bool = False):
    conn = await get_connection()

    if only_new:
        reports = await conn.fetch(
            """
            SELECT id, user_id, username, district, category, description, address, contact, status, created_at
            FROM reports
            WHERE status = $1
            ORDER BY id DESC
            LIMIT 20
            """,
            "Нове"
        )
    else:
        reports = await conn.fetch(
            """
            SELECT id, user_id, username, district, category, description, address, contact, status, created_at
            FROM reports
            ORDER BY id DESC
            LIMIT 20
            """
        )

    await conn.close()

    if not reports:
        if only_new:
            await message.answer("Нових звернень немає.", reply_markup=admin_menu)
        else:
            await message.answer("Звернень поки немає.", reply_markup=admin_menu)
        return

    text = "📥 Нові звернення:\n\n" if only_new else "📚 Останні звернення:\n\n"

    for report in reports:
        username = f"@{report['username']}" if report["username"] else "Не вказано"

        text += (
            f"№{report['id']}\n"
            f"Дата: {report['created_at'] or 'Не вказано'}\n"
            f"Район: {report['district'] or 'Не вказано'}\n"
            f"Тип: {report['category'] or 'Не вказано'}\n"
            f"Статус: {report['status'] or 'Нове'}\n"
            f"Користувач: {username}\n"
            f"Telegram ID: {report['user_id'] or 'Не вказано'}\n"
            f"Опис: {report['description'] or 'Не вказано'}\n"
            f"Адреса: {report['address'] or 'Не вказано'}\n"
            f"Контакт: {report['contact'] or 'Не вказано'}\n\n"
        )

    await send_long_message(message, text, reply_markup=admin_menu)


@dp.message(CommandStart())
async def start(message: Message):
    user_states.pop(message.from_user.id, None)

    if is_admin(message.from_user.id):
        await message.answer(
            "Привіт 👋\n\n"
            "Ти увійшов як адміністратор.\n"
            "Можеш переглядати звернення та змінювати їхній статус.",
            reply_markup=admin_menu
        )
        return

    await message.answer(
        "Привіт 👋\n\n"
        "Це бот Деснянського району Києва.\n"
        "Тут ти можеш залишити скаргу, пропозицію або повідомити про проблему.",
        reply_markup=main_menu
    )


@dp.message(Command("admin"))
async def admin_command(message: Message):
    user_states.pop(message.from_user.id, None)

    if not is_admin(message.from_user.id):
        await message.answer("У тебе немає доступу до адмінки.")
        return

    await message.answer(
        "🛠 Адмінка відкрита.\n\n"
        "Тут можна переглядати звернення та змінювати їхній статус.",
        reply_markup=admin_menu
    )


@dp.message(F.text == "📥 Нові звернення")
async def admin_new_reports(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У тебе немає доступу до адмінки.")
        return

    await show_reports(message, only_new=True)


@dp.message(F.text == "📚 Усі звернення")
async def admin_all_reports(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У тебе немає доступу до адмінки.")
        return

    await show_reports(message, only_new=False)


@dp.message(F.text == "🔄 Змінити статус")
async def change_status_start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У тебе немає доступу до адмінки.")
        return

    user_states[message.from_user.id] = {
        "step": "admin_wait_report_id"
    }

    await message.answer(
        "Введи номер звернення, якому потрібно змінити статус.\n\n"
        "Наприклад: 12",
        reply_markup=admin_menu
    )


@dp.message(F.text == "⬅️ Вийти з адмінки")
async def exit_admin(message: Message):
    user_states.pop(message.from_user.id, None)

    await message.answer(
        "Ти повернувся у звичайне меню.",
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

    if is_admin(message.from_user.id):
        await message.answer(
            "Повертаємось в адмін-меню.",
            reply_markup=admin_menu
        )
        return

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
        await message.answer("У тебе поки немає звернень.", reply_markup=main_menu)
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

    await send_long_message(message, text, reply_markup=main_menu)


@dp.message(F.text == "☎️ Корисні контакти")
async def contacts(message: Message):
    await message.answer(
        "Корисні контакти:\n\n"
        "Приймальня Деснянської районної в місті Києві державної адміністрації (РДА): 0(44)515-66-66\n"
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
            reply_markup=admin_menu if is_admin(user_id) else main_menu
        )
        return

    if state["step"] == "admin_wait_report_id":
        if not is_admin(user_id):
            await message.answer("У тебе немає доступу до адмінки.")
            return

        if not message.text.isdigit():
            await message.answer(
                "Введи тільки номер звернення.\n\n"
                "Наприклад: 12",
                reply_markup=admin_menu
            )
            return

        report_id = int(message.text)

        conn = await get_connection()

        report = await conn.fetchrow(
            """
            SELECT id, status
            FROM reports
            WHERE id = $1
            """,
            report_id
        )

        await conn.close()

        if not report:
            await message.answer(
                f"Звернення №{report_id} не знайдено.\n\n"
                "Спробуй ввести інший номер.",
                reply_markup=admin_menu
            )
            return

        state["report_id"] = report_id
        state["step"] = "admin_wait_status"

        await message.answer(
            f"Звернення №{report_id} знайдено.\n"
            f"Поточний статус: {report['status'] or 'Нове'}\n\n"
            "Тепер обери новий статус:",
            reply_markup=status_menu
        )
        return

    if state["step"] == "admin_wait_status":
        if not is_admin(user_id):
            await message.answer("У тебе немає доступу до адмінки.")
            return

        allowed_statuses = ["Нове", "В роботі", "Виконано", "Відхилено"]

        if message.text not in allowed_statuses:
            await message.answer(
                "Будь ласка, обери статус із кнопок.",
                reply_markup=status_menu
            )
            return

        report_id = state["report_id"]
        new_status = message.text

        conn = await get_connection()

        result = await conn.execute(
            """
            UPDATE reports
            SET status = $1
            WHERE id = $2
            """,
            new_status,
            report_id
        )

        await conn.close()
        user_states.pop(user_id, None)

        if result == "UPDATE 0":
            await message.answer(
                f"Звернення №{report_id} не знайдено.",
                reply_markup=admin_menu
            )
            return

        await message.answer(
            f"✅ Статус звернення №{report_id} змінено на: {new_status}",
            reply_markup=admin_menu
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
