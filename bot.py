import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

TOKEN = "8072842801:AAHgOyzmksuZrYOGnoSSYmsgVEOKUxklMcA"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- БАЗА ГРАВЦІВ ---
players = {}

def get_player(user_id):
    if user_id not in players:
        players[user_id] = {
            "balance": 0,
            "collection": set()
        }
    return players[user_id]

# --- 100% ТІЛЬКИ ТЮЛЕНІ (СТАБІЛЬНІ ПРЯМІ ПОСИЛАННЯ) ---
SEAL_PHOTOS = [
    "https://raw.githubusercontent.com/TelegramBots/book/master/src/concept/photo.jpg", # Запасне фото
    "https://cdn.pixabay.com/photo/2016/12/13/22/39/seals-1905292_1280.jpg",
    "https://cdn.pixabay.com/photo/2019/08/19/13/58/seal-4416521_1280.jpg",
    "https://cdn.pixabay.com/photo/2017/08/06/12/06/seal-2591905_1280.jpg",
    "https://cdn.pixabay.com/photo/2020/03/11/15/45/seal-4922485_1280.jpg"
]

TITLES_EPIC = [
    "Повелитель Айсбергів", "Адмірал Глибин", "Примарний Тюлень", "Крижаний Воїн", 
    "Сонний Тюлень", "Хранитель Океану", "Шпигун Холодного Моря", "Мастер Риболовлі",
    "Король Ластів", "Великий Вусань", "Гроза Атлантики", "Морський Ніндзя"
]

CARDS_DATABASE = {}

for card_id in range(1, 101):
    if card_id <= 50:
        rarity, weight = "⚪ Звичайна (Common)", 50
        prefix = "Обучений"
    elif card_id <= 80:
        rarity, weight = "🔵 Рідкісна (Rare)", 30
        prefix = "Шляхетний"
    elif card_id <= 95:
        rarity, weight = "🟣 Епічна (Epic)", 15
        prefix = "Легендарний"
    else:
        rarity, weight = "🟡 МІФІЧНА (Legendary)", 5
        prefix = "Божественний"

    title = random.choice(TITLES_EPIC)
    card_name = f"{prefix} {title} #{card_id}"
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
    builder.button(text="🎣 Ловити рибу (Заробити TL)", callback_data="fish")
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

# --- ОБРОБНИКИ КОМАНД ТА КНОПОК ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_player(message.from_user.id)
    await message.answer(
        "🦭 **Вітаю у Seal Game!**\n\n"
        "1. Лови рибу, щоб заробляти **TL**.\n"
        "2. Витрачай TL на купівлю **100 унікальних карток тюленів** (1 картка = 10 TL).\n"
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
    earned_tl = random.randint(2, 15)
    player["balance"] += earned_tl
    
    fish_types = ["🐟 Маленьку рибку", "🐠 Тропічну рибку", "🐟 Велику тріску", "🦀 Краба", "🦐 Креветку"]
    caught = random.choice(fish_types)
    
    text = (
        f"🎣 **Вдала риболовля!**\n\n"
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
        f"📦 Зібрано карток: **{len(player['collection'])} / 100**"
    )
    await callback.message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "buy_card")
async def process_buy_card(callback: types.CallbackQuery):
    player = get_player(callback.from_user.id)
    
    if player["balance"] < 10:
        await callback.answer("❌ Нестача коштів! Спочатку злови рибу і зароби 10 TL.", show_alert=True)
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
    
    try:
        await callback.message.answer_photo(
            photo=chosen_card["image"],
            caption=caption,
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
    except Exception:
        await callback.message.answer(caption, reply_markup=get_back_keyboard(), parse_mode="Markdown")

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

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
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
