from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.enums import ParseMode
import asyncio
import os

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привіт 👋\n\n"
        "Це бот району Києва.\n"
        "Тут ти можеш залишити скаргу, пропозицію або повідомити про проблему."
    )


@dp.message()
async def echo(message: Message):
    await message.answer(
        f"Твоє повідомлення отримано:\n\n{message.text}"
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
