import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GAME_URL = os.getenv("GAME_URL", "https://skypulse.vercel.app")  # убедитесь, что ссылка правильная

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Создаём клавиатуру с одной кнопкой, открывающей WebApp
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Играть в SkyPulse", web_app=WebAppInfo(url=GAME_URL))]
        ]
    )
    await message.answer(
        "Добро пожаловать в SkyPulse!\n"
        "Нажимай на кнопку, чтобы запустить игру.",
        reply_markup=keyboard
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())