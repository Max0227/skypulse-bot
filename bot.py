import asyncio
import logging
import json
import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GAME_URL = os.getenv("GAME_URL", "https://skypulse.vercel.app")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('scores.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS scores
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  score INTEGER,
                  level INTEGER,
                  wagons INTEGER,
                  meters INTEGER,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

RULES_TEXT = """
🌟 **SkyPulse: Пятый элемент** 🌟

Ты управляешь жёлтым такси из будущего. Собирай монеты, уклоняйся от препятствий и увеличивай свой состав!

🚖 **Управление:** тап по экрану – прыжок.
🪙 **Монеты:** золотые дают +1, цветные дают бонусы.
🚃 **Вагоны:** каждые 15 монет добавляют вагон. Чем длиннее состав, тем сложнее, но и зрелищнее.
💎 **Магазин:** улучшай свой корабль за монеты.
🏆 **Таблица лидеров:** соревнуйся с друзьями!

Команды:
/start – начать
/rules – правила
/top – топ-100 игроков
/mybest – личный рекорд
"""

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Играть в SkyPulse", web_app=WebAppInfo(url=GAME_URL))]
        ]
    )
    await message.answer(
        f"Привет, {message.from_user.first_name or 'пилот'}! 👋\n"
        "Это игра SkyPulse – такси-поезд в стиле Пятого элемента.\n"
        "Нажми на кнопку, чтобы начать, или /rules для правил.",
        reply_markup=keyboard
    )

@dp.message(Command("rules"))
async def cmd_rules(message: types.Message):
    await message.answer(RULES_TEXT, parse_mode="Markdown")

@dp.message(Command("top"))
async def cmd_top(message: types.Message):
    conn = sqlite3.connect('scores.db')
    c = conn.cursor()
    c.execute('''SELECT username, first_name, score, level, wagons, meters 
                 FROM scores 
                 ORDER BY score DESC 
                 LIMIT 100''')
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await message.answer("🏆 Пока нет рекордов. Сыграй и стань первым!")
        return
    
    text = "🏆 **ТОП-100 ИГРОКОВ** 🏆\n\n"
    for i, row in enumerate(rows, 1):
        name = row[1] or row[0] or "Аноним"
        medal = ""
        if i == 1:
            medal = "🥇 "
        elif i == 2:
            medal = "🥈 "
        elif i == 3:
            medal = "🥉 "
        elif i <= 10:
            medal = "⭐ "
        text += f"{medal}{i}. {name} — {row[2]} очков (ур.{row[3]}, 🚃 {row[4]}, 📏 {row[5]}м)\n"
        if i == 50:
            text += "\n... и ещё 50"
            break
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("mybest"))
async def cmd_mybest(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('scores.db')
    c = conn.cursor()
    c.execute('''SELECT score, level, wagons, meters, timestamp 
                 FROM scores WHERE user_id = ?''', (user_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        await message.answer("📊 У тебя пока нет сохранённых результатов. Сыграй и возвращайся!")
    else:
        await message.answer(
            f"📊 **Твой лучший результат**\n\n"
            f"🎯 Очки: {row[0]}\n"
            f"📊 Уровень: {row[1]}\n"
            f"🚃 Вагонов: {row[2]}\n"
            f"📏 Метров: {row[3]}\n"
            f"📅 Дата: {row[4][:10]}",
            parse_mode="Markdown"
        )

@dp.message()
async def handle_webapp_data(message: types.Message):
    if message.web_app_data:
        data = json.loads(message.web_app_data.data)
        user = message.from_user
        
        conn = sqlite3.connect('scores.db')
        c = conn.cursor()
        c.execute('SELECT score FROM scores WHERE user_id = ?', (user.id,))
        old = c.fetchone()
        
        if not old or data['score'] > old[0]:
            c.execute('''INSERT OR REPLACE INTO scores 
                         (user_id, username, first_name, score, level, wagons, meters)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (user.id, user.username, user.first_name,
                       data['score'], data['level'], data['wagons'], data['meters']))
            conn.commit()
            await message.answer("✅ Новый рекорд сохранён!")
        else:
            await message.answer("📊 Результат сохранён (но это не лучше твоего рекорда)")
        
        conn.close()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
