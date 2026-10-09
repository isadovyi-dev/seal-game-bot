import os
import random
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage2
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web
import aioredis
import asyncpg
from dotenv import load_dotenv

load_dotenv()

# Конфигурация
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
DATABASE_URL = os.environ.get("DATABASE_URL")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
PORT = int(os.environ.get("PORT", 8080))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seal_game_bot")

# Константы карточек
CARD_NAMES = [
    "🦭 Сонний Тюленчик", "🦭 Малий Вусань", "🦭 Пухлик", "🦭 Морська Коржика", "🦭 Рибоєд",
    "🦭 Товстун", "🦭 Любитель Сну", "🦭 Пляжний Лежень", "🦭 Плямістий Тюлень", "🦭 Маленький Пловець"
]

CARDS_DATABASE = {}
for idx in range(1, 101):
    if idx <= 50:
        rarity, weight = "⭐ Звичайна", 50
    elif idx <= 80:
        rarity, weight = "🟥 Рідкісна", 30
    elif idx <= 95:
        rarity, weight = "🟦 Епічний", 15
    else:
        rarity, weight = "🟥 Міфічний", 5
    CARDS_DATABASE[idx] = {
        "id": idx,
        "name": f"{CARD_NAMES[idx % 10]} #{idx}",
        "rarity": rarity,
        "weight": weight
    }

# Глобальные переменные
PROCESSING_USERS = {}
ADMINS_SET = set()
SEAL_PHOTOS = {}
DB_POOL = None

# Инициализация БД
async def init_db():
    global DB_POOL, SEAL_PHOTOS
    DB_POOL = await asyncpg.create_pool(DATABASE_URL)
    async with DB_POOL.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id BIGINT PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 0,
                collection INTEGER[] NOT NULL DEFAULT '{}',
                fish_attempts INTEGER NOT NULL DEFAULT 0,
                last_fish_date TEXT NOT NULL DEFAULT '',
                username TEXT NOT NULL DEFAULT ''
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY,
                file_id TEXT NOT NULL
            )
        """)
        photo_rows = await conn.fetch("SELECT * FROM photos")
        for row in photo_rows:
            SEAL_PHOTOS[row["id"]] = row["file_id"]

async def save_player(user_id: int, player: Dict):
    async with DB_POOL.acquire() as conn:
        await conn.execute("""
            INSERT INTO players (user_id, balance, collection, fish_attempts, last_fish_date, username)
            VALUES ($1, $2, $3::integer[], $4, $5, $6)
            ON CONFLICT (user_id) DO UPDATE SET
                balance = $2,
                collection = $3::integer[],
                fish_attempts = $4,
                last_fish_date = $5,
                username = $6
        """, user_id, player["balance"], list(player["collection"]), player["fish_attempts"], player["last_fish_date"], player["username"])

async def get_player_data(user_id: int, username: Optional[str] = None) -> Dict:
    today_str = datetime.now().strftime("%Y-%m-%d")
    async with DB_POOL.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not row:
            await conn.execute("""
                INSERT INTO players (user_id, balance, collection, fish_attempts, last_fish_date, username)
                VALUES ($1, 0, '{}', 0, $2, $3)
            """, user_id, today_str, (username or "").lower())
            row = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        player = {
            "balance": row["balance"],
            "collection": set(row["collection"]),
            "fish_attempts": row["fish_attempts"],
            "last_fish_date": row["last_fish_date"],
            "username": row["username"]
        }
        if username and player["username"] != (username or "").lower():
            player["username"] = (username or "").lower()
            await save_player(user_id, player)
        if player["last_fish_date"] != today_str:
            player["fish_attempts"] = 0
            player["last_fish_date"] = today_str
            await save_player(user_id, player)
        return player

def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎣 Ловити рибу (2/день)", callback_data="fish")
    builder.button(text="🛒 Купити картку (10 TL)", callback_data="buy_card")
    builder.button(text="📊 Моя колекція", callback_data="my_collection")
    builder.button(text="💰 Профіль", callback_data="profile")
    builder.adjust(1)
    return builder.as_markup()

def get_back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎣 Ловити ще", callback_data="fish")
    builder.button(text="🛒 Купити картку (10 TL)", callback_data="buy_card")
    builder.button(text="🏠 Головне меню", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()

class AdminStates(StatesGroup):
    waiting_for_password = State()

bot = Bot(token=BOT_TOKEN)
redis = aioredis.from_url(REDIS_URL)
dp = Dispatcher(storage=RedisStorage2(redis=redis))

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    username = message.from_user.username
    await get_player_data(message.from_user.id, username)
    await message.answer(
        "🦭 **Вітаю у Seal Game!**\n\n"
        "1. 🎣 Лови рибу (2 спроби на день)\n"
        "2. Купуй картки тюленів за TL\n"
        "3. Збирай колекцію!",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    if message.from_user.id in ADMINS_SET:
        await message.answer(f"🔑 Ви адмін! Завантажено фото: {len(SEAL_PHOTOS)}/100", parse_mode="Markdown")
        return
    await state.set_state(AdminStates.waiting_for_password)
    await message.answer("🔐 Введіть пароль адміна:", parse_mode="Markdown")

@dp.message(AdminStates.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    if message.text and message.text.strip() == ADMIN_PASSWORD:
        ADMINS_SET.add(message.from_user.id)
        await state.clear()
        await message.answer(f"✅ Пароль вірний! Завантажено фото: {len(SEAL_PHOTOS)}/100", parse_mode="Markdown")
    else:
        await message.answer("❌ Невірний пароль!", parse_mode="Markdown")

@dp.message(F.photo)
async def handle_photo_upload(message: types.Message):
    if message.from_user.id not in ADMINS_SET:
        return
    async with DB_POOL.acquire() as conn:
        next_id = await conn.fetchval("SELECT COALESCE(MAX(id), 0) + 1 FROM photos")
        if next_id > 100:
            await message.answer("✅ Уже 100 фото!")
            return
        file_id = message.photo[-1].file_id
        SEAL_PHOTOS[next_id] = file_id
        await conn.execute("INSERT INTO photos (id, file_id) VALUES ($1, $2) ON CONFLICT (id) DO UPDATE SET file_id = $2", next_id, file_id)
        await message.answer(f"📸 Завантажено photo #{next_id}! Залишилося: {100 - next_id} шт.", parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "fish")
async def process_fish(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in PROCESSING_USERS:
        await callback.answer("⏳ Зачекай...", show_alert=False)
        return
    PROCESSING_USERS[user_id] = datetime.now()
    try:
        player = await get_player_data(user_id, callback.from_user.username)
        if player["fish_attempts"] >= 2:
            await callback.message.answer("⏳ Ліміт ловлі вичерпано! (2/2 на день)", reply_markup=get_main_keyboard(), parse_mode="Markdown")
            await callback.answer()
            return
        player["fish_attempts"] += 1
        earned_tl = random.randint(5, 12)
        player["balance"] += earned_tl
        await save_player(user_id, player)
        await callback.message.answer(
            f"🎣 Вдала ловля! ({player['fish_attempts']}/2)\n\n💰 Зароблено: +{earned_tl} TL\n💵 Баланс: {player['balance']} TL",
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()
    finally:
        if user_id in PROCESSING_USERS:
            del PROCESSING_USERS[user_id]

@dp.callback_query(lambda c: c.data == "profile")
async def process_profile(callback: types.CallbackQuery):
    player = await get_player_data(callback.from_user.id, callback.from_user.username)
    collected_ids = player["collection"]
    text = (
        f"👤 **Профіль:**\n\n"
        f"💰 Баланс: {player['balance']} TL\n"
        f"🎣 Спроби сьогодні: {player['fish_attempts']}/2\n"
        f"📊 Колекція: {len(collected_ids)}/100"
    )
    await callback.message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "buy_card")
async def process_buy_card(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in PROCESSING_USERS:
        await callback.answer("⏳ Обробка...", show_alert=False)
        return
    PROCESSING_USERS[user_id] = datetime.now()
    try:
        player = await get_player_data(user_id, callback.from_user.username)
        if player["balance"] < 10:
            await callback.message.answer(f"❌ Не вистачає TL! (Потрібно 10 TL, у вас {player['balance']})", reply_markup=get_main_keyboard(), parse_mode="Markdown")
            await callback.answer()
            return
        available_cards = [c for c in CARDS_DATABASE.values() if c["id"] not in player["collection"]]
        if not available_cards:
            await callback.message.answer("✅ У вас всі картки!", reply_markup=get_main_keyboard(), parse_mode="Markdown")
            await callback.answer()
            return
        weights = [c["weight"] for c in available_cards]
        chosen_card = random.choices(available_cards, weights=weights, k=1)[0]
        player["balance"] -= 10
        player["collection"].add(chosen_card["id"])
        await save_player(user_id, player)
        card_photo = SEAL_PHOTOS.get(chosen_card["id"])
        caption = f"🛒 {chosen_card['name']}\n✨ Рідкість: {chosen_card['rarity']}\n💰 Баланс: {player['balance']} TL"
        if card_photo:
            await callback.message.answer_photo(photo=card_photo, caption=caption, reply_markup=get_back_keyboard(), parse_mode="Markdown")
        else:
            await callback.message.answer(caption, reply_markup=get_back_keyboard(), parse_mode="Markdown")
        await callback.answer()
    finally:
        if user_id in PROCESSING_USERS:
            del PROCESSING_USERS[user_id]

@dp.callback_query(lambda c: c.data == "my_collection")
async def process_collection(callback: types.CallbackQuery):
    player = await get_player_data(callback.from_user.id, callback.from_user.username)
    collected_ids = sorted(list(player["collection"]))
    if not collected_ids:
        await callback.message.answer("📭 Колекція порожня!", reply_markup=get_main_keyboard(), parse_mode="Markdown")
        await callback.answer()
        return
    text = f"📊 **Колекція ({len(collected_ids)}/100):**"
    builder = InlineKeyboardBuilder()
    for card_id in collected_ids:
        card = CARDS_DATABASE[card_id]
        builder.button(text=card["name"], callback_data=f"view_card_{card_id}")
    builder.button(text="🏠 Головне меню", callback_data="main_menu")
    builder.adjust(1)
    await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "main_menu")
async def process_main_menu(callback: types.CallbackQuery):
    await callback.message.answer("🦭 Головне меню", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    await callback.answer()

async def handle_ping(request):
    return web.Response(text="Bot and Web Server are running!")

async def handle_add_tl(request):
    try:
        data = await request.json()
        username = data.get("username", "").strip().replace("@", "")
        amount = int(data.get("amount", 0))
        if not username or amount <= 0:
            return web.json_response({"status": "error", "message": "Invalid data"}, status=400)
        async with DB_POOL.acquire() as conn:
            user_id = await conn.fetchval("SELECT user_id FROM players WHERE username = $1", username.lower())
            if not user_id:
                return web.json_response({"status": "error", "message": "User not found"}, status=404)
            new_balance = await conn.fetchval("UPDATE players SET balance = balance + $1 WHERE user_id = $2 RETURNING balance", amount, user_id)
        return web.json_response({"status": "ok", "new_balance": new_balance, "added": amount})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_post("/api/add-tl", handle_add_tl)
    from aiohttp.web_middlewares import cors_middleware
    cors = cors_middleware(allow_all=True)
    app.middlewares.append(cors)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

async def main():
    await init_db()
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
