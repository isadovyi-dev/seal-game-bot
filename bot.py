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

# --- ТИМЧАСОВА БАЗА ГРАВЦІВ В ПАМ'ЯТІ ---
# (У майбутньому можна підключити SQLite / PostgreSQL)
players = {}

def get_player(user_id):
    if user_id not in players:
        players[user_id] = {
            "balance": 100,  # Стартовий баланс 100 TL
            "collection": set() # Збережені унікальні ID карток (від 1 до 100)
        }
    return players[user_id]

# --- ГЕНЕРАЦІЯ 100 УНІКАЛЬНИХ КАРТОК ---
# Картинка за замовчуванням (можна замінити на свої посилання або photo_id)
DEFAULT_SEAL_IMAGE = "https://images.unsplash.com/photo-1598439210625-5067c578f3f6?w=800"

CARDS_DATABASE = {}
for card_id in range(1, 101):
    if card_id <= 50:
        rarity, weight = "⚪ Звичайна (Common)", 50
    elif card_id <= 80:
        rarity, weight = "🔵 Рідкісна (Rare)", 30
    elif card_id <= 95:
        rarity, weight = "🟣 Епічна (Epic)", 15
    else:
        rarity, weight = "🟡 Легендарна (Legendary)", 5

    CARDS_DATABASE[card_id] = {
        "id": card_id,
        "name": f"Тюлень #{card_id}",
        "rarity": rarity,
        "weight": weight,
        "image": DEFAULT_SEAL_IMAGE
    }

# --- КЛАВІАТУРИ ---
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🃏 Купити картку (10 TL)", callback_data="buy_card")
    builder.button(text="📦 Моя колекція", callback_data="my_collection")
    builder.button(text="💰 Профіль / Баланс", callback_data="profile")
    builder.adjust(1)
    return builder.as_markup()

def get_back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Купити ще (10 TL)", callback_data="buy_card")
    builder.button(text="🏠 Головне меню", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()

# --- ОБРОБНИКИ КОМАНД ТА КНОПОК ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_player(message.from_user.id)
    await message.answer(
        "🦭 **Вітаю у Seal Game!**\n\n"
        "Збирай унікальну колекцію з **100 карток тюленів**!\n"
        "• Вартість 1 картки: **10 TL**\n"
        "• Бонус за збір усієї колекції (100/100): **+1000 TL**!",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "main_menu")
async def process_main_menu(callback: types.CallbackQuery):
    await callback.message.answer(
        "🦭 **Головне меню**",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
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
    
    # Перевірка балансу
    if player["balance"] < 10:
        await callback.answer("❌ Нестача коштів! Картка коштує 10 TL.", show_alert=True)
        return

    # Знімаємо 10 TL
    player["balance"] -= 10
    
    # Вибираємо картку з урахуванням шансів рідкісності
    cards_list = list(CARDS_DATABASE.values())
    weights = [c["weight"] for c in cards_list]
    chosen_card = random.choices(cards_list, weights=weights, k=1)[0]
    
    # Перевіряємо чи була така картка раніше
    is_new = chosen_card["id"] not in player["collection"]
    player["collection"].add(chosen_card["id"])
    
    status_text = "✨ **НОВА КАРТКА У КОЛЕКЦІЮ!**" if is_new else "🔄 Така картка вже є (повторка)."
    
    # Перевірка на супер-бонус за 100/100 карток
    bonus_text = ""
    if len(player["collection"]) == 100 and is_new:
        player["balance"] += 1000
        bonus_text = "\n\n🎉 **ВІТАЄМО! Ти зібрав усі 100 карток і отримав бонус +1000 TL!** 🏆"

    caption = (
        f"{status_text}\n\n"
        f"🃏 **{chosen_card['name']}**\n"
        f"✨ Рідкісність: {chosen_card['rarity']}\n"
        f"💰 Залишок балансу: **{player['balance']} TL**\n"
        f"📦 Колекція: **{len(player['collection'])}/100**"
        f"{bonus_text}"
    )
    
    # Відправляємо фото тюленя з підписом та кнопками
    try:
        await callback.message.answer_photo(
            photo=chosen_card["image"],
            caption=caption,
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
    except Exception:
        # Якщо фото не завантажилося, надсилаємо текстом
        await callback.message.answer(caption, reply_markup=get_back_keyboard(), parse_mode="Markdown")

    await callback.answer()

@dp.callback_query(lambda c: c.data == "my_collection")
async def process_collection(callback: types.CallbackQuery):
    player = get_player(callback.from_user.id)
    count = len(player["collection"])
    
    await callback.message.answer(
        f"📦 **Твоя колекція:**\n\n"
        f"Зібрано: **{count} з 100** унікальних карток тюленів.\n"
        f"Залишилося знайти: **{100 - count}**.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (НЕ ЧІПАТИ) ---
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
