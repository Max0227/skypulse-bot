import asyncio
import logging
import os
import sys
from typing import Optional

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Получаем токен и URL игры
BOT_TOKEN = os.getenv("BOT_TOKEN")
GAME_URL = os.getenv("GAME_URL", "https://skypulse.vercel.app")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN не задан! Установите переменную окружения.")
    # Вместо sys.exit выбрасываем исключение, чтобы Railway показал ошибку в логах
    raise ValueError("BOT_TOKEN is not set")

# Инициализация бота (без parse_mode в конструкторе!)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ----------------------------------------------------------------------
# Текст правил (Markdown)
# ----------------------------------------------------------------------
RULES_TEXT = f"""
{hbold('🌟 Добро пожаловать в SkyPulse: Пятый элемент! 🌟')}

Ты управляешь легендарным жёлтым такси из будущего. Твоя цель – пролететь как можно дальше, собирая монеты и уклоняясь от препятствий.

{hbold('🚖 Как играть:')}
• Нажимай на экран, чтобы такси подпрыгивало.
• Пролетая через ворота, получаешь очки и продвигаешься по уровням.
• Собирай монеты (золотые и цветные), чтобы увеличивать свой состав.
• Каждые 10 монет к твоему такси пристыковывается новый вагончик! Максимум – 10 вагонов.
• Вагончики делают игру сложнее, но и зрелищнее. Если вагон врежется в препятствие – он отвалится.
• Головное такси уязвимо: любое его столкновение – конец игры.

{hbold('🌈 Бонусные монетки:')}
• 🔴 Красная – ускорение (x2 к очкам)
• 🔵 Синяя – щит (временная неуязвимость)
• 🟢 Зелёная – магнит (притягивает монеты)
• 🟣 Фиолетовая – замедление времени

{hbold('🏆 Прогрессия:')}
С каждым уровнем скорость растёт, а проходы сужаются. Сколько вагонов ты сможешь накопить?

{hbold('🎮 Управление:')}
Просто тапай по экрану – такси взлетает. Управляй ритмом, чтобы пройти между препятствиями.

{hbold('📊 Таблица лидеров (скоро!):')}
В будущем ты сможешь соревноваться с другими игроками и видеть топ лучших.

Нажми кнопку ниже, чтобы начать игру!
"""

# ----------------------------------------------------------------------
# Команда /start
# ----------------------------------------------------------------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Играть в SkyPulse", web_app=WebAppInfo(url=GAME_URL))]
        ]
    )
    await message.answer(
        f"Привет, {message.from_user.first_name or 'пилот'}! 👋\n\n"
        "Это игра SkyPulse – такси-поезд в стиле Пятого элемента.\n"
        "Нажми на кнопку, чтобы начать, или используй /rules для подробных правил.",
        reply_markup=keyboard
    )

# ----------------------------------------------------------------------
# Команда /rules – подробные правила
# ----------------------------------------------------------------------
@dp.message(Command("rules"))
async def cmd_rules(message: types.Message):
    await message.answer(RULES_TEXT, parse_mode=ParseMode.MARKDOWN)

# ----------------------------------------------------------------------
# Команда /game – просто кнопка для игры
# ----------------------------------------------------------------------
@dp.message(Command("game"))
async def cmd_game(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚖 Играть сейчас", web_app=WebAppInfo(url=GAME_URL))]
        ]
    )
    await message.answer("Нажми кнопку, чтобы запустить игру:", reply_markup=keyboard)

# ----------------------------------------------------------------------
# Обработчик данных из WebApp (для будущей таблицы лидеров)
# ----------------------------------------------------------------------
@dp.message()
async def handle_webapp_data(message: types.Message):
    if message.web_app_data:
        data = message.web_app_data.data
        user = message.from_user
        logger.info(f"Получены данные от {user.full_name} (id={user.id}): {data}")
        # Здесь позже будет сохранение в БД
        await message.answer(
            f"✅ Результат получен! Спасибо за игру.\n"
            f"Твои данные: {data}\n\n"
            f"Скоро здесь появится таблица рекордов!"
        )

# ----------------------------------------------------------------------
# Запуск бота
# ----------------------------------------------------------------------
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен и готов к работе")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
    except Exception as e:
        logger.exception("Критическая ошибка: %s", e)
        raise
