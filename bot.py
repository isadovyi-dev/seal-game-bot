import os
import random
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

TOKEN = "8072842801:AAHgOyzmksuZrYOGnoSSYmsgVEOKUxklMcA"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- БАЗА ГРАВЦІВ (у пам'яті) ---
players = {}

def get_player(user_id):
    if user_id not in players:
        players[user_id] = {
            "balance": 0,
            "collection": set(),
            "fish_attempts": 0,
            "last_fish_reset": datetime.now()
        }
    
    # Скидання ліміту риболовлі кожні 24 години
    player = players[user_id]
    if datetime.now() - player["last_fish_reset"] > timedelta(days=1):
        player["fish_attempts"] = 0
        player["last_fish_reset"] = datetime.now()
        
    return player

# --- 100% ПЕРЕВІРЕНІ ТЮЛЕНІ ---
SEAL_PHOTOS = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/7/79/Common_seal_2007-08-12.jpg/800px-Common_seal_2007-08-12.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Harbor_seal_at_Kachemak_Bay.jpg/800px-Harbor_seal_at_Kachemak_Bay.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Harbor_Seal_%28Phoca_vitulina%29_-_San_Diego%2C_CA.jpg/800px-Harbor_Seal_%28Phoca_vitulina%29_-_San_Diego%2C_CA.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Phoca_vitulina_1.jpg/800px-Phoca_vitulina_1.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Harbor_seal_resting.jpg/800px-Harbor_seal_resting.jpg"
]

ADJECTIVES = ["Арктичний", "Примарний", "Крижаний", "Штормовий", "Грозний", "Сонний", "Броньований", "Космічний", "Вогняний", "Забутий", "Епічний", "Нічний"]
TITLES = ["Берсерк", "Адмірал", "Шпигун", "Захисник", "Вусань", "Мисливець", "Володар", "Ніндзя", "Капітан", "Вартовий", "Мандрівник", "Титан"]

CARDS_DATABASE = {}
used_names = set()

for card_id in range(1, 101):
    if card_id <= 50:
        rarity, weight = "⚪ Звичайна (Common)", 50
    elif card_id <= 80:
        rarity, weight = "🔵 Рідкісна (Rare)", 30
    elif card_id <= 95:
        rarity, weight = "🟣 Епічна (Epic)", 15
    else:
        rarity, weight = "🟡 МІФІЧНА (Legendary)", 5

    while True:
        card_name = f"🦭 {random.choice(ADJECTIVES)} {random.choice(TITLES)} #{card_id}"
        if card_name not in used_names:
            used_names.add(card_name)
            break

    photo_url = SEAL_PHOTOS[(card_id - 1) % len(SEAL_PHOTOS)]

    CARDS_DATABASE[card_id] = {
        "id": card_id,
        "name": card_name,
        "rarity": rarity,
        "weight": weight,
        "image": photo_url
    }

# --- КЛАВІАТУРИ ---
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎣 Ловити рибу (Макс 2/день)", callback_data="fish")
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

# --- ОБРОБНИКИ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_player(message.from_user.id)
    await message.answer(
        "🦭 **Вітаю у Seal Game!**\n\n"
        "1. Лови рибу (максимум **2 рази на день**).\n"
        "2. Витрачай TL на купівлю **100 унікальних карток** (1 картка = 10 TL).\n"
        "3. Збери всю колекцію (100/100) та отримай бонус **+1000 TL**!",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "main_menu")
async def process_main_menu(callback: types.CallbackQuery):
    await callback.message.answer("🦭 **Головне меню**", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "fish")
async def process_fish(callback: types.CallbackQuery):
    player = get_player(callback.from_user.id)
    
    # Перевірка ліміту риболовлі (2 рази на день)
    if player["fish_attempts"] >= 2:
        await callback.message.answer(
            "⏳ **Ліміт риболовлі вичерпано!**\n\n"
            "Ти вже зловив рибу 2 рази сьогодні. Приходь завтра!",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    player["fish_attempts"] += 1
    earned_tl = random.randint(5, 12)
    player["balance"] += earned_tl
    
    fish_types = ["🐟 Маленьку рибку", "🐠 Тропічну рибку", "🐟 Велику тріску", "🦀 Краба", "🦐 Креветку"]
    caught = random.choice(fish_types)
    
    text = (
        f"🎣 **Вдала риболовля!** ({player['fish_attempts']}/2 сьогодні)\n\n"
        f"Ти спіймав: **{caught}**\n"
        f"Зароблено: **+{earned_tl} TL** 💰\n"
        f"Твій баланс: **{player['balance']} TL**"
    )
    
    await callback.message.answer(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "profile")
async def process_profile(callback: types.CallbackQuery):
    player = get_player(callback.from_user.id)
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
    player = get_player(callback.from_user.id)
    
    if player["balance"] < 10:
        await callback.message.answer(
            f"❌ **Нестача коштів!**\n\n"
            f"Картка коштує **10 TL**, а у тебе **{player['balance']} TL**.\n"
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
    
    status_text = "✨ **НОВА УНІКАЛЬНА КАРТКА!**" if is_new else "🔄 Така картка вже є в колекції."
    
    bonus_text = ""
    if len(player["collection"]) == 100 and is_new:
        player["balance"] += 1000
        bonus_text = "\n\n🎉 **ВІТАЄМО! Ти зібрав усі 100 карток і отримав бонус +1000 TL!** 🏆"

    caption = (
        f"{status_text}\n\n"
        f"🃏 **Картка:** {chosen_card['name']}\n"
        f"✨ **Рідкісність:** {chosen_card['rarity']}\n"
        f"💰 **Залишок балансу:** {player['balance']} TL\n"
        f"📦 **Колекція:** {len(player['collection'])}/100"
        f"{bonus_text}"
    )
    
    await callback.message.answer_photo(
        photo=chosen_card["image"],
        caption=caption,
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )

    await callback.answer()

@dp.callback_query(lambda c: c.data == "my_collection")
async def process_collection(callback: types.CallbackQuery):
    player = get_player(callback.from_user.id)
    count = len(player["collection"])
    
    await callback.message.answer(
        f"📦 **Твоя колекція:**\n\n"
        f"Зібрано: **{count} з 100** унікальних карток.\n"
        f"Залишилося знайти: **{100 - count}**.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

# --- ВЕБ-СЕРВЕР ---
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
