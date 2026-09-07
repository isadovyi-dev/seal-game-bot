import os
import json
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

TOKEN = "8072842801:AAHgOyzmksuZrYOGnoSSYmsgVEOKUxklMcA"
ADMIN_PASSWORD = "2345"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DB_FILE = "players_data.json"
PHOTOS_FILE = "seal_photos.json"
PROCESSING_USERS = set()
ADMINS_SET = set()

class AdminStates(StatesGroup):
    waiting_for_password = State()

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for user_id, p in data.items():
                    p["collection"] = set(p["collection"])
                return {int(k): v for k, v in data.items()}
        except Exception:
            return {}
    return {}

def save_db():
    data_to_save = {}
    for user_id, p in PLAYERS_DB.items():
        p_copy = p.copy()
        p_copy["collection"] = list(p["collection"])
        data_to_save[str(user_id)] = p_copy
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)

def load_photos():
    if os.path.exists(PHOTOS_FILE):
        try:
            with open(PHOTOS_FILE, "r", encoding="utf-8") as f:
                return {int(k): v for k, v in json.load(f).items()}
        except Exception:
            return {}
    return {}

def save_photos():
    with open(PHOTOS_FILE, "w", encoding="utf-8") as f:
        json.dump(SEAL_PHOTOS, f, ensure_ascii=False, indent=2)

PLAYERS_DB = load_db()
SEAL_PHOTOS = load_photos()

def get_player_data(user_id: int):
    today_str = datetime.now().strftime("%Y-%m-%d")
    if user_id not in PLAYERS_DB:
        PLAYERS_DB[user_id] = {
            "balance": 0,
            "collection": set(),
            "fish_attempts": 0,
            "last_fish_date": today_str
        }
        save_db()
    player = PLAYERS_DB[user_id]
    if player["last_fish_date"] != today_str:
        player["fish_attempts"] = 0
        player["last_fish_date"] = today_str
        save_db()
    return player

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

# --- АДМІНКА ---
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    if message.from_user.id in ADMINS_SET:
        await message.answer(
            f"👑 **Ви вже в режимі адміна!**\n\n"
            f"Завантажено фотографій: **{len(SEAL_PHOTOS)} / 100**\n\n"
            f"Просто надсилайте фотографії тюленів сюди у чат по черзі або альбомом.",
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
            f"📊 Наразі завантажено фотографій: **{len(SEAL_PHOTOS)} / 100**\n\n"
            "📸 **Що робити далі:**\n"
            "Просто надсилай фотографії тюленів у чат! Бот сам прив'яже їх по черзі до кожної картки від #1 до #100.",
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ **Невірний пароль! Спробуйте ще раз або введіть /start:**", parse_mode="Markdown")

@dp.message(F.photo)
async def handle_photo_upload(message: types.Message):
    if message.from_user.id not in ADMINS_SET:
        return

    next_id = len(SEAL_PHOTOS) + 1
    if next_id > 100:
        await message.answer("✅ **Усі 100 фотографій вже успішно завантажені!**")
        return

    file_id = message.photo[-1].file_id
    SEAL_PHOTOS[next_id] = file_id
    save_photos()

    card_name = CARDS_DATABASE[next_id]["name"]
    await message.answer(
        f"📸 **Завантажено photo #{next_id}!**\n"
        f"Прив'язано до: **{card_name}**\n"
        f"Залишилося: **{100 - next_id}** шт.",
        parse_mode="Markdown"
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    get_player_data(message.from_user.id)
    await message.answer(
        "🦭 **Вітаю у Seal Game!**\n\n"
        "1. Лови рибу (максимум **2 рази на день**).\n"
        "2. Витрачай TL на купівлю **100 унікальних карток** (1 картка = 10 TL).\n"
        "3. Збирай колекцію!",
        reply_markup=get_main_keyboard(),
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
        player = get_player_data(user_id)
        if player["fish_attempts"] >= 2:
            await callback.message.answer(
                "⏳ **Ліміт риболовлі вичерпано!**\n\n"
                "Ти вже зловив рибу 2 рази сьогодні (2/2). Приходь завтра!",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
            await callback.answer()
            return

        player["fish_attempts"] += 1
        earned_tl = random.randint(5, 12)
        player["balance"] += earned_tl
        save_db()
        
        fish_types = ["🐟 Маленьку рибку", "🐠 Тропічну рибку", "🐟 Велику тріску", "🦀 Краба", "🦐 Креветку"]
        caught = random.choice(fish_types)
        
        text = (
            f"🎣 **Вдала риболовля!** ({player['fish_attempts']}/2 сьогодні)\n\n"
            f"Ти спіймав: **{caught}**\n"
            f"Зароблено: **+{earned_tl} TL** 💰\n"
            f"Твій новий баланс: **{player['balance']} TL**"
        )
        
        await callback.message.answer(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")
        await callback.answer()
    finally:
        PROCESSING_USERS.remove(user_id)

@dp.callback_query(lambda c: c.data == "profile")
async def process_profile(callback: types.CallbackQuery):
    player = get_player_data(callback.from_user.id)
    text = (
        f"👤 **Твій профіль:**\n\n"
        f"💰 Баланс: **{player['balance']} TL**\n"
        f"🎣 Спроб риболовлі сьогодні: **{player['fish_attempts']} / 2**\n"
        f"📦 Зібрано карток: **{len(player['collection'])} / 100**\n"
        f"🖼 Завантажено фотографій в систему: **{len(SEAL_PHOTOS)} / 100**"
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
        player = get_player_data(user_id)
        if player["balance"] < 10:
            await callback.message.answer(
                f"❌ **Нестача коштів!**\n\n"
                f"Картка коштує **10 TL**, а у тебе зараз **{player['balance']} TL**.\n"
                f"Зароби гроші на риболовлі!",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
            await callback.answer()
            return

        player["balance"] -= 10
        cards_list = list(CARDS_DATABASE.values())
        weights = [c["weight"] for c in cards_list]
        chosen_card = random.choices(cards_list, weights=weights, k=1)[0]
        
        is_new = chosen_card["id"] not in player["collection"]
        player["collection"].add(chosen_card["id"])
        
        bonus_text = ""
        if len(player["collection"]) == 100 and is_new:
            player["balance"] += 1000
            bonus_text = "\n\n🎉 **ВІТАЄМО! Ти зібрав усі 100 карток і отримав бонус +1000 TL!** 🏆"

        save_db()

        status_text = "✨ **НОВА УНІКАЛЬНА КАРТКА!**" if is_new else "🔄 Така картка вже є в колекції."
        caption = (
            f"{status_text}\n\n"
            f"🃏 **Картка:** {chosen_card['name']}\n"
            f"✨ **Рідкісність:** {chosen_card['rarity']}\n"
            f"💰 **Залишок балансу:** {player['balance']} TL\n"
            f"📦 **Колекція:** {len(player['collection'])}/100"
            f"{bonus_text}"
        )

        card_photo = SEAL_PHOTOS.get(chosen_card["id"])
        if card_photo:
            await callback.message.answer_photo(
                photo=card_photo,
                caption=caption,
                reply_markup=get_back_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await callback.message.answer(
                caption,
                reply_markup=get_back_keyboard(),
                parse_mode="Markdown"
            )

        await callback.answer()
    finally:
        PROCESSING_USERS.remove(user_id)

@dp.callback_query(lambda c: c.data == "my_collection")
async def process_collection(callback: types.CallbackQuery):
    player = get_player_data(callback.from_user.id)
    collected_ids = sorted(list(player["collection"]))
    
    if not collected_ids:
        text = "📦 **Твоя колекція порожня!**\n\nКупи свою першу картку в магазині за 10 TL."
        builder = InlineKeyboardBuilder()
        builder.button(text="🃏 Купити картку (10 TL)", callback_data="buy_card")
        builder.button(text="🏠 Головне меню", callback_data="main_menu")
        builder.adjust(1)
        await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
        await callback.answer()
        return

    text = f"📦 **Твоя колекція ({len(collected_ids)}/100):**\n\nОбери картку для перегляду:\n"
    builder = InlineKeyboardBuilder()
    for card_id in collected_ids:
        card = CARDS_DATABASE[card_id]
        builder.button(text=f"{card['name']} [{card['rarity'].split()[0]}]", callback_data=f"view_card_{card_id}")
    
    builder.button(text="🏠 Головне меню", callback_data="main_menu")
    builder.adjust(1)
    await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("view_card_"))
async def process_view_card(callback: types.CallbackQuery):
    card_id = int(callback.data.split("_")[2])
    card = CARDS_DATABASE.get(card_id)
    if card:
        caption = (
            f"🃏 Картка:\n"
            f"✨ Рідкісність:"
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="📦 Назад до колекції", callback_data="my_collection")
        builder.button(text="🏠 Головне меню", callback_data="main_menu")
        builder.adjust(1)

        card_photo = SEAL_PHOTOS.get(card_id)
        if card_photo:
            await callback.message.answer_photo(
                photo=card_photo,
                caption=caption,
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )
        else:
            await callback.message.answer(
                caption,
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )
    await callback.answer()

async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
