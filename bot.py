import asyncio
import json
import os
import random
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# ==================== НАЛАШТУВАННЯ ====================
BOT_TOKEN = "8072842801:AAHgOyzmksuZrYOGnoSSYmsgVEOKUxklMcA"
DB_FILE = "users.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(users_db, f, ensure_ascii=False, indent=2)

users_db = load_db()

# ЦІНА ВІДКРИТТЯ КЕЙСА
CASE_PRICE = 10 

# ==================== 100 КАРТОК ТА ШАНСИ ====================
RARITIES = {
    "common": {"name": "⚪ Звичайна", "chance": 60, "income": 1},      # 60% шанс
    "rare": {"name": "🟢 Рідкісна", "chance": 25, "income": 5},       # 25% шанс
    "epic": {"name": "🔵 Епічна", "chance": 10, "income": 20},        # 10% шанс
    "legendary": {"name": "🟣 Легендарна", "chance": 4, "income": 100},# 4% шанс
    "mythic": {"name": "🟡 Міфічна", "chance": 1, "income": 500}       # 1% шанс
}

CARDS = {}
rarity_keys = list(RARITIES.keys())

# Генеруємо 100 карток з унікальними тюленями
for i in range(1, 101):
    r_key = rarity_keys[(i - 1) // 20]
    r_data = RARITIES[r_key]
    
    CARDS[f"card_{i}"] = {
        "id": f"card_{i}",
        "name": f"{r_data['name']} Тюлень #{i}",
        "rarity_key": r_key,
        "rarity_name": r_data["name"],
        "income": r_data["income"],
        "image": f"https://picsum.photos/seed/seal_{i}_card/400/400"
    }

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_user_data(username):
    username = str(username).lower().replace("@", "")
    if username not in users_db:
        users_db[username] = {"balance": 0, "cards": []}
        save_db()
    return users_db[username]

# Функція рандомного випадіння за шансами
def roll_card():
    rand = random.randint(1, 100)
    cumulative = 0
    selected_rarity = "common"
    
    for r_key, r_data in RARITIES.items():
        cumulative += r_data["chance"]
        if rand <= cumulative:
            selected_rarity = r_key
            break
            
    # Вибираємо випадкову картку з цієї рідкісності
    pool = [c for c in CARDS.values() if c["rarity_key"] == selected_rarity]
    return random.choice(pool)

# ==================== ХЕНДЛЕРИ ТЕЛЕГРАМ ====================

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    username = message.from_user.username or f"user_{message.from_user.id}"
    user = get_user_data(username)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎁 Відкрити Кейс ({CASE_PRICE} TL)", callback_query_data="open_case")],
        [InlineKeyboardButton(text="🎴 Моя колекція карток", callback_query_data="my_cards")],
        [InlineKeyboardButton(text="💰 Мій баланс", callback_query_data="balance")]
    ])
    
    await message.answer(
        f"Привіт, @{username}!\n"
        f"Твій баланс: <b>{user['balance']} TL</b>\n"
        f"Зібрано карток: <b>{len(user['cards'])} / 100</b>\n\n"
        f"Відкривай кейси за <b>{CASE_PRICE} TL</b> та вибивай рідкісні, епічні й міфічні картки!",
        parse_mode="HTML",
        reply_markup=kb
    )

# Відкриття кейса
@dp.callback_query(F.data == "open_case")
async def open_case(call: types.CallbackQuery):
    username = call.from_user.username or f"user_{call.from_user.id}"
    user = get_user_data(username)
    
    if user["balance"] < CASE_PRICE:
        await call.answer(f"❌ Не вистачає монет! Відкриття коштує {CASE_PRICE} TL.", show_alert=True)
        return

    # Знімаємо монети
    user["balance"] -= CASE_PRICE
    
    # Вибиваємо картку
    dropped_card = roll_card()
    
    if dropped_card["id"] not in user["cards"]:
        user["cards"].append(dropped_card["id"])
    save_db()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔄 Відкрити ще раз ({CASE_PRICE} TL)", callback_query_data="open_case")],
        [InlineKeyboardButton(text="« Меню", callback_query_data="main_menu")]
    ])
    
    caption_text = (
        f"🎉 <b>ВИ ВИТЯГЛИ КАРТКУ!</b>\n\n"
        f"Картка: <b>{dropped_card['name']}</b>\n"
        f"Рідкісність: <b>{dropped_card['rarity_name']}</b>\n"
        f"📈 Пасивний дохід: <b>+{dropped_card['income']} TL/сек</b>\n\n"
        f"💰 Залишок балансу: <b>{user['balance']} TL</b>"
    )
    
    await call.message.answer_photo(
        photo=dropped_card["image"],
        caption=caption_text,
        parse_mode="HTML",
        reply_markup=kb
    )
    await call.answer()

# Перегляд своєї колекції
@dp.callback_query(F.data == "my_cards")
async def show_my_cards(call: types.CallbackQuery):
    username = call.from_user.username or f"user_{call.from_user.id}"
    user = get_user_data(username)
    
    if not user["cards"]:
        await call.answer("У тебе ще немає жодної картки! Відкривай кейси.", show_alert=True)
        return
        
    cards_list = "\n".join([f"• {CARDS[c_id]['name']}" for c_id in user["cards"][:15]])
    total_count = len(user["cards"])
    
    await call.message.answer(
        f"<b>🎴 Твоя колекція ({total_count}/100):</b>\n\n"
        f"{cards_list}\n"
        f"{'<i>...та інші</i>' if total_count > 15 else ''}",
        parse_mode="HTML"
    )
    await call.answer()

@dp.callback_query(F.data == "balance")
async def show_balance(call: types.CallbackQuery):
    username = call.from_user.username or f"user_{call.from_user.id}"
    user = get_user_data(username)
    await call.answer(f"Твій баланс: {user['balance']} TL | Карток: {len(user['cards'])}/100", show_alert=True)

# ==================== ЗВ'ЯЗОК З ГРОЮ (API) ====================

async def handle_add_tl(request):
    try:
        data = await request.json()
        username = data.get("username")
        amount = data.get("amount", 0)
        
        if username:
            user = get_user_data(username)
            user["balance"] += amount
            save_db()
            return web.json_response({"status": "ok", "new_balance": user["balance"]})
    except Exception as e:
        logging.error(f"Error in API: {e}")
    return web.json_response({"status": "error"}, status=400)

async def start_web_server():
    app = web.Application()
    app.router.add_post('/api/add-tl', handle_add_tl)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 8080)
    await site.start()

# ==================== ЗАПУСК ====================

async def main():
    logging.basicConfig(level=logging.INFO)
    await start_web_server()
    print("🚀 Бот з кейсами успішно запущено!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())