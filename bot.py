import asyncio
import logging
import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    WebAppInfo
)
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
    logger.error("BOT_TOKEN не задан!")
    sys.exit(1)

# Инициализация бота
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# ----------------------------------------------------------------------
# База данных SQLite (с абсолютным путём)
# ----------------------------------------------------------------------
DB_PATH = Path(__file__).parent / "skypulse.db"

def init_db():
    """Создаёт таблицу users, если её нет."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            best_score INTEGER DEFAULT 0,
            best_level INTEGER DEFAULT 0,
            total_meters INTEGER DEFAULT 0,
            total_coins INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            last_play DATE
        )
    """)
    conn.commit()
    conn.close()
    logger.info(f"База данных инициализирована по пути {DB_PATH}")

init_db()

def update_user_stats(user_id: int, username: str, first_name: str, score: int, level: int, meters: int):
    """Обновляет статистику пользователя в БД."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT best_score, best_level, total_meters, games_played FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        today = datetime.now().date().isoformat()

        if row:
            best_score, best_level, total_meters, games_played = row
            new_best_score = max(best_score, score)
            new_best_level = max(best_level, level)
            new_total_meters = total_meters + meters
            new_games_played = games_played + 1
            cur.execute("""
                UPDATE users SET
                    username = ?, first_name = ?,
                    best_score = ?, best_level = ?,
                    total_meters = ?, games_played = ?,
                    last_play = ?
                WHERE user_id = ?
            """, (username, first_name, new_best_score, new_best_level,
                  new_total_meters, new_games_played, today, user_id))
        else:
            cur.execute("""
                INSERT INTO users
                (user_id, username, first_name, best_score, best_level, total_meters, games_played, last_play)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, first_name, score, level, meters, 1, today))

        conn.commit()
        conn.close()
        logger.info(f"Статистика обновлена для user_id={user_id}, score={score}")
    except Exception as e:
        logger.error(f"Ошибка обновления БД: {e}")

def get_top_users(limit: int = 10):
    """Возвращает топ игроков по best_score."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT username, first_name, best_score, best_level, total_meters
        FROM users
        ORDER BY best_score DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_user_stats(user_id: int):
    """Возвращает статистику конкретного пользователя."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT best_score, best_level, total_meters, games_played, last_play
        FROM users WHERE user_id = ?
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

# ----------------------------------------------------------------------
# Клавиатура для быстрого доступа
# ----------------------------------------------------------------------
def get_main_keyboard():
    """Возвращает Reply-клавиатуру с основными командами."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Играть"), KeyboardButton(text="📊 Топ")],
            [KeyboardButton(text="📜 Правила"), KeyboardButton(text="🏆 Мой рекорд")]
        ],
        resize_keyboard=True
    )

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
    # Отправляем клавиатуру
    await message.answer("Выбери действие:", reply_markup=get_main_keyboard())

# ----------------------------------------------------------------------
# Команда /rules
# ----------------------------------------------------------------------
@dp.message(Command("rules"))
@dp.message(lambda msg: msg.text and msg.text.lower() == "📜 правила")
async def cmd_rules(message: types.Message):
    await message.answer(RULES_TEXT)

# ----------------------------------------------------------------------
# Команда /game (и кнопка "Играть")
# ----------------------------------------------------------------------
@dp.message(Command("game"))
@dp.message(lambda msg: msg.text and msg.text.lower() == "🚀 играть")
async def cmd_game(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚖 Играть сейчас", web_app=WebAppInfo(url=GAME_URL))]
        ]
    )
    await message.answer("Нажми кнопку, чтобы запустить игру:", reply_markup=keyboard)

# ----------------------------------------------------------------------
# Команда /top
# ----------------------------------------------------------------------
@dp.message(Command("top"))
@dp.message(lambda msg: msg.text and msg.text.lower() == "📊 топ")
async def cmd_top(message: types.Message):
    top = get_top_users(10)
    if not top:
        await message.answer("Пока нет ни одного игрока в таблице лидеров.")
        return

    text = "🏆 *ТОП-10 ИГРОКОВ* 🏆\n\n"
    for i, (username, first_name, best_score, best_level, total_meters) in enumerate(top, 1):
        name = username or first_name or "Аноним"
        text += f"{i}. {name} — {best_score} очков (ур. {best_level}, {total_meters} м)\n"

    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

# ----------------------------------------------------------------------
# Команда /mybest
# ----------------------------------------------------------------------
@dp.message(Command("mybest"))
@dp.message(lambda msg: msg.text and msg.text.lower() == "🏆 мой рекорд")
async def cmd_mybest(message: types.Message):
    user_id = message.from_user.id
    stats = get_user_stats(user_id)
    if not stats:
        await message.answer("Вы ещё не играли. Сыграйте, чтобы появилась статистика!")
        return

    best_score, best_level, total_meters, games_played, last_play = stats
    text = (
        f"📊 *Ваша статистика*\n\n"
        f"🏆 Лучший счёт: {best_score}\n"
        f"🌟 Лучший уровень: {best_level}\n"
        f"📏 Всего метров: {total_meters}\n"
        f"🎮 Сыграно игр: {games_played}\n"
        f"📅 Последняя игра: {last_play}"
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

# ----------------------------------------------------------------------
# Обработчик обычных сообщений (возвращает клавиатуру)
# ----------------------------------------------------------------------
@dp.message()
async def handle_other_messages(message: types.Message):
    """Если пользователь отправил обычное сообщение, напоминаем о кнопках."""
    await message.answer(
        "Используй кнопки ниже для навигации 👇",
        reply_markup=get_main_keyboard()
    )

# ----------------------------------------------------------------------
# Обработчик данных из WebApp
# ----------------------------------------------------------------------
@dp.message()
async def handle_webapp_data(message: types.Message):
    if not message.web_app_data:
        return

    try:
        data = json.loads(message.web_app_data.data)
        logger.info(f"Получены данные от {message.from_user.id}: {data}")
    except json.JSONDecodeError:
        logger.error(f"Невалидный JSON: {message.web_app_data.data}")
        await message.answer("Ошибка обработки данных. Попробуйте ещё раз.")
        return

    user = message.from_user
    score = data.get('score', 0)
    level = data.get('level', 1)
    meters = data.get('meters', 0)

    update_user_stats(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        score=score,
        level=level,
        meters=meters
    )

    await message.answer(
        f"✅ Результат сохранён!\n"
        f"Счёт: {score} | Уровень: {level} | Метров: {meters}\n\n"
        f"Используй /top для просмотра лидеров."
    )

# ----------------------------------------------------------------------
# Текст правил (вынесен отдельно для читаемости)
# ----------------------------------------------------------------------
RULES_TEXT = f"""
{hbold('🌟 Добро пожаловать в SkyPulse: Пятый элемент! 🌟')}

Ты управляешь легендарным жёлтым такси из будущего. Твоя цель – пролететь как можно дальше, собирая монеты и уклоняясь от препятствий.

{hbold('🚖 Как играть:')}
• Нажимай на экран, чтобы такси подпрыгивало.
• Пролетая через ворота, получаешь очки и продвигаешься по уровням.
• Собирай монеты (золотые и цветные), чтобы увеличивать свой состав.
• Каждые 15 монет к твоему такси пристыковывается новый вагончик! Максимум – 12 вагонов (можно увеличить в магазине).
• Вагончики делают игру сложнее, но и зрелищнее. Если вагон врежется в препятствие – он отвалится.
• Головное такси уязвимо: у него есть здоровье (сердечки). При потере всех сердечек – конец игры.

{hbold('🌈 Бонусные монетки:')}
• 🔴 Красная – ускорение (x2 к очкам)
• 🔵 Синяя – щит (временная неуязвимость)
• 🟢 Зелёная – магнит (притягивает монеты)
• 🟣 Фиолетовая – замедление времени

{hbold('🏆 Прогрессия:')}
С каждым уровнем скорость растёт, а проходы сужаются. Каждые 10 уровней появляется планета-станция – коснись её, чтобы получить бонус за каждый вагон и открыть магазин.

{hbold('🎮 Управление:')}
Просто тапай по экрану – такси взлетает. Управляй ритмом, чтобы пройти между препятствиями.

{hbold('📊 Таблица лидеров:')}
Используй команду /top, чтобы увидеть лучших игроков.
"""

# ----------------------------------------------------------------------
# Запуск бота
# ----------------------------------------------------------------------
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
