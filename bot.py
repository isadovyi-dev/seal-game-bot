import os
import random
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web
import asyncpg

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
DATABASE_URL = os.environ["DATABASE_URL"]

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

PROCESSING_USERS = set()
ADMINS_SET = set()

PLAYERS_DB = {}
SEAL_PHOTOS = {}
DB_POOL = None


class AdminStates(StatesGroup):
    waiting_for_password = State()


async def init_db():
    global DB_POOL
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

        rows = await conn.fetch("SELECT * FROM players")
        for row in rows:
            PLAYERS_DB[row["user_id"]] = {
                "balance": row["balance"],
                "collection": set(row["collection"]),
                "fish_attempts": row["fish_attempts"],
                "last_fish_date": row["last_fish_date"],
                "username": row["username"]
            }

        photo_rows = await conn.fetch("SELECT * FROM photos")
        for row in photo_rows:
            SEAL_PHOTOS[row["id"]] = row["file_id"]


async def save_player(user_id: int):
    p = PLAYERS_DB[user_id]
    async with DB_POOL.acquire() as conn:
        await conn.execute("""
            INSERT INTO players (user_id, balance, collection, fish_attempts, last_fish_date, username)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (user_id) DO UPDATE SET
                balance = $2, collection = $3, fish_attempts = $4, last_fish_date = $5, username = $6
        """, user_id, p["balance"], list(p["collection"]), p["fish_attempts"], p["last_fish_date"], p["username"])


async def save_photo(photo_id: int, file_id: str):
    async with DB_POOL.acquire() as conn:
        await conn.execute("""
            INSERT INTO photos (id, file_id) VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE SET file_id = $2
        """, photo_id, file_id)


async def get_player_data(user_id: int, username: str = None):
    today_str = datetime.now().strftime("%Y-%m-%d")
    is_new = user_id not in PLAYERS_DB
    if is_new:
        PLAYERS_DB[user_id] = {
            "balance": 0,
            "collection": set(),
            "fish_attempts": 0,
            "last_fish_date": today_str,
            "username": username.lower() if username else ""
        }
    player = PLAYERS_DB[user_id]
    changed = is_new
    if username and player["username"] != username.lower():
        player["username"] = username.lower()
        changed = True
    if player["last_fish_date"] != today_str:
        player["fish_attempts"] = 0
        player["last_fish_date"] = today_str
        changed = True
    if changed:
        await save_player(user_id)
    return player


def find_user_by_username(username: str):
    clean_name = username.replace("@", "").strip().lower()
    for uid, data in PLAYERS_DB.items():
        if data.get("username", "").lower() == clean_name:
            return uid
    return None


CARD_NAMES = [
    "🦭 Сонний Тюленчик", "🦭 Малий Вусань", "🦭 Пухлик", "🦭 Морська Коржика", "🦭 Рибоед",
    "🦭 Товстун", "🦭 Любитель Сну", "🦭 Пляжний Лежень", "🦭 Плямистий Тюлень", "🦭 Маленький Пловець",
    "🦭 Вусатий Друг", "🦭 Сніжний Тюлень", "🦭 Морозний Пухляш", "🦭 Морський Батон", "🦭 Рибний Злодій",
    "🦭 Ситий Вусань", "🦭 Спокійний Тюлень", "🦭 Сонячний Гребець", "🦭 Тюлень-Нирець", "🦭 Ластоногий",
    "🦭 Морський Млинчик", "🦭 Береговий Вартовий", "🦭 Кумедний Тюлень", "🦭 Веселий Нирець", "🦭 Тихоокеанський Вусань",
    "🦭 Білобрюхий Тюлень", "🦭 Полярний Малюк", "🦭 Тюлень-Чилюган", "🦭 Дрімач", "🦭 Денний Лежень",
    "🦭 Любитель Тріски", "🦭 Морський Бублик", "🦭 Сніговий Вусань", "🦭 Холодний Носик", "🦭 Водяний Тюлень",
    "🦭 Пухнастий Ласт", "🦭 Острівний Тюлень", "🦭 Гребець Глибин", "🦭 Тюлень-Ласун", "🦭 Морський Вусань",
    "🦭 Риболов Малюк", "🦭 Сірий Тюлень", "🦭 Плямистий Нирець", "🦭 Арктичний Пухлик", "🦭 Морський Сплюх",
    "🦭 Тюлень-Карапуз", "🦭 Морозний Вусань", "🦭 Малий Глибинник", "🦭 Океанський Дружок", "🦭 Тюлень-Ластоног",
    "🦭 Штормовий Плавець", "🦭 Мисливець за Лососем", "🦭 Глибинний Шпигун", "🦭 Північний Страж", "🦭 Срібний Вусань",
    "🦭 Капітан Ластів", "🦭 Арктичний Мисливець", "🦭 Крижаний Нирець", "🦭 Повелитель Волн", "🦭 Швидкісний Тюлень",
    "🦭 Гроза Тріски", "🦭 Страж Айсбергів", "🦭 Темноводний Тюлень", "🦭 Сталевий Вусань", "🦭 Нічний Пловець",
    "🦭 Полярний Капітан", "🦭 Морський Снайпер", "🦭 Сріблястий Страж", "🦭 Майстер Риболовлі", "🦭 Океанський Блукач",
    "🦭 Штормовий Вусань", "🦭 Морозний Страж", "🦭 Глибинний Шукач", "🦭 Морський Вовк", "🦭 Полярний Розвідник",
    "🦭 Арктичний Захисник", "🦭 Вонистий Тюлень", "🦭 Легенда Рибалок", "🦭 Срібний Ласт", "🦭 Примарний Нирець",
    "🦭 Адмірал Холодних Морей", "🦭 Володар Айсбергів", "🦭 Примарний Вусань", "🦭 Страж Північного Сяйва", "🦭 Глибинний Титан",
    "🦭 Атлантичний Воїн", "🦭 Володар Полярних Вод", "🦭 Крижаний Берсерк", "🦭 Тюлень-Ніндзя", "🦭 Король Глибин",
    "🦭 Штормовий Титан", "🦭 Арктичний Легендар", "🦭 Страж Океану", "🦭 Примарний Мисливець", "🦭 Володар Течій",
    "🦭 Божественний Тюлень Океану", "🦭 Древній Хранитель Глибин", "🦭 Легендарний Повелитель Штормів", "🦭 Полярний Властелик Світу", "🦭 Нефритовий Божественний Вусань"
]

CARDS_DATABASE = {}
for idx in range(1, 101):
    if idx <= 50:
        rarity, weight = "⚪ Звичайна", 50
    elif idx <= 80:
        rarity, weight = "🔵 Рідкісна", 30
    elif idx <= 95:
        rarity, weight = "🟣 Епічна", 15
    else:
        rarity, weight = "🟡 МІФІЧНА", 5
    CARDS_DATABASE[idx] = {
        "id": idx,
        "name": f"{CARD_NAMES[idx - 1]} #{idx}",
        "rarity": rarity,
        "weight": weight
    }


def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎣 Ловити рибу (2/день)", callback_data="fish")
    builder.button(text="🃏 Купити картку (10 TL)", callback_data="buy_card")
    builder.button(text="📦 Моя колекція", callback_data="my_collection")
    builder.button(text="💰 Профіль / Баланс", callback_data="profile")
    builder.adjust(1)
    return builder.as_markup()


def get_back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎣 Ловити ще", callback_data="fish")
    builder.button(text="🔄 Купити картку (10 TL)", callback_data="buy_card")
    builder.button(text="🏠 Головне меню", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    username = message.from_user.username or ""
    await get_player_data(message.from_user.id, username)
    await message.answer(
        "🦭 **Вітаю у Seal Game!**\n\n"
        "1. Лови рибу (максимум **2 рази на день**).\n"
        "2. Витрачай TL на купівлю **100 унікальних карток** (1 картка = 10 TL).\n"
        "3. Збирай колекцію!",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )


@dp.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    if message.from_user.id in ADMINS_SET:
        await message.answer(
            f"👑 **Ви в режимі адміна!**\n\n"
            f"Завантажено фотографій: **{len(SEAL_PHOTOS)} / 100**",
            parse_mode="Markdown"
        )
    else:
        await state.set_state(AdminStates.waiting_for_password)
        await message.answer("🔒 **Введіть пароль адміна:**", parse_mode="Markdown")


@dp.message(AdminStates.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    if message.text and message.text.strip() == ADMIN_PASSWORD:
        ADMINS_SET.add(message.from_user.id)
        await state.clear()
        await message.answer(
            "✅ **Пароль вірний! Режим адміна активовано.**\n\n"
            f"📊 Наразі завантажено фотографій: **{len(SEAL_PHOTOS)} / 100**",
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ **Невірний пароль!**", parse_mode="Markdown")


@dp.message(F.photo)
async def handle_photo_upload(message: types.Message):
    if message.from_user.id not in ADMINS_SET:
        return
    next_id = len(SEAL_PHOTOS) + 1
    if next_id > 100:
        await message.answer("✅ Усі 100 фотографій вже завантажені!")
        return
    file_id = message.photo[-1].file_id
    SEAL_PHOTOS[next_id] = file_id
    await save_photo(next_id, file_id)
    await message.answer(
        f"📸 **Завантажено photo #{next_id}!**\n"
        f"Залишилося: **{100 - next_id}** шт.",
        parse_mode="Markdown"
    )


@dp.callback_query(lambda c: c.data == "main_menu")
async def process_main_menu(callback: types.CallbackQuery):
    await callback.message.answer("🦭 **Головне меню**", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "fish")
async def process_fish(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in PROCESSING_USERS:
        await callback.answer("⏳ Зачекай...", show_alert=False)
        return
    PROCESSING_USERS.add(user_id)
    try:
        player = await get_player_data(user_id, callback.from_user.username)
        if player["fish_attempts"] >= 2:
            await callback.message.answer(
                "⏳ **Ліміт риболовлі вичерпано!** (2/2 на день)",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
            await callback.answer()
            return
        player["fish_attempts"] += 1
        earned_tl = random.randint(5, 12)
        player["balance"] += earned_tl
        await save_player(user_id)
        text = (
            f"🎣 **Вдала риболовля!** ({player['fish_attempts']}/2)\n\n"
            f"Зароблено: **+{earned_tl} TL** 💰\n"
            f"Твій новий баланс: **{player['balance']} TL**"
        )
        await callback.message.answer(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")
        await callback.answer()
    finally:
        PROCESSING_USERS.remove(user_id)


@dp.callback_query(lambda c: c.data == "profile")
async def process_profile(callback: types.CallbackQuery):
    player = await get_player_data(callback.from_user.id, callback.from_user.username)
    text = (
        f"👤 **Твій профіль:**\n\n"
        f"💰 Баланс: **{player['balance']} TL**\n"
        f"🎣 Спроб риболовлі сьогодні: **{player['fish_attempts']} / 2**\n"
        f"📦 Зібрано карток: **{len(player['collection'])} / 100**"
    )
    await callback.message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "buy_card")
async def process_buy_card(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in PROCESSING_USERS:
        await callback.answer("⏳ Обробка...", show_alert=False)
        return
    PROCESSING_USERS.add(user_id)
    try:
        player = await get_player_data(user_id, callback.from_user.username)
        if player["balance"] < 10:
            await callback.message.answer(
                f"❌ **Нестача коштів!** (Картка коштує 10 TL, у тебе {player['balance']} TL)",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
            await callback.answer()
            return
        player["balance"] -= 10
        cards_list = list(CARDS_DATABASE.values())
        weights = [c["weight"] for c in cards_list]
        chosen_card = random.choices(cards_list, weights=weights, k=1)[0]
        player["collection"].add(chosen_card["id"])
        await save_player(user_id)
        caption = (
            f"🃏 **Картка:** {chosen_card['name']}\n"
            f"✨ **Рідкісність:** {chosen_card['rarity']}\n"
            f"💰 **Залишок балансу:** {player['balance']} TL"
        )
        card_photo = SEAL_PHOTOS.get(chosen_card["id"])
        if card_photo:
            await callback.message.answer_photo(photo=card_photo, caption=caption, reply_markup=get_back_keyboard(), parse_mode="Markdown")
        else:
            await callback.message.answer(caption, reply_markup=get_back_keyboard(), parse_mode="Markdown")
        await callback.answer()
    finally:
        PROCESSING_USERS.remove(user_id)


@dp.callback_query(lambda c: c.data == "my_collection")
async def process_collection(callback: types.CallbackQuery):
    player = await get_player_data(callback.from_user.id, callback.from_user.username)
    collected_ids = sorted(list(player["collection"]))
    if not collected_ids:
        text = "📦 **Твоя колекція порожня!**"
        builder = InlineKeyboardBuilder()
        builder.button(text="🏠 Головне меню", callback_data="main_menu")
        await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
        await callback.answer()
        return
    text = f"📦 **Твоя колекція ({len(collected_ids)}/100):**\n"
    builder = InlineKeyboardBuilder()
    for card_id in collected_ids:
        card = CARDS_DATABASE[card_id]
        builder.button(text=f"{card['name']}", callback_data=f"view_card_{card_id}")
    builder.button(text="🏠 Головне меню", callback_data="main_menu")
    builder.adjust(1)
    await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()


# --- ВЕБ-ІНТЕРФЕЙС ТА API ДЛЯ ГРИ ---
async def handle_ping(request):
    return web.Response(text="Bot and Web Server are running!")


async def handle_add_tl(request):
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        amount = int(data.get("amount", 0))
        if not username or amount <= 0:
            return web.json_response({"status": "error", "message": "Invalid input"}, status=400)
        user_id = find_user_by_username(username)
        if not user_id:
            return web.json_response({"status": "error", "message": "User not found in bot. Press /start in bot first!"}, status=404)
        player = PLAYERS_DB[user_id]
        player["balance"] += amount
        await save_player(user_id)
        return web.json_response({
            "status": "ok",
            "new_balance": player["balance"],
            "added": amount
        })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)


async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    app.router.add_post('/api/add-tl', handle_add_tl)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    await init_db()
    await start_web_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
