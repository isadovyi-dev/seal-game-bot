import os
import random
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

TOKEN = "8072842801:AAHgOyzmksuZrYOGnoSSYmsgVEOKUxklMcA"

bot = Bot(token=TOKEN)
dp = Dispatcher()

PLAYERS_DB = {}
PROCESSING_USERS = set()

def get_player_data(user_id: int):
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if user_id not in PLAYERS_DB:
        PLAYERS_DB[user_id] = {
            "balance": 0,
            "collection": set(),
            "fish_attempts": 0,
            "last_fish_date": today_str
        }
    
    player = PLAYERS_DB[user_id]
    
    if player["last_fish_date"] != today_str:
        player["fish_attempts"] = 0
        player["last_fish_date"] = today_str
        
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

# Прямі швидкі посилання на зображення
SEAL_IMAGES = [
    "https://images.unsplash.com/photo-1598439210625-5067c578f3f6?w=800",
    "https://images.unsplash.com/photo-1551085254-e96b210db58a?w=800",
    "https://images.unsplash.com/photo-1575550959106-5a7defe28b56?w=800",
    "https://images.unsplash.com/photo-1534567153574-2b12153a87f0?w=800"
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
        "weight": weight,
        "image": SEAL_IMAGES[(idx - 1) % len(SEAL_IMAGES)]
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
async def cmd_start(message: types.Message):
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
        await callback.answer()
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
        f"📦 Зібрано карток: **{len(player['collection'])} / 100**"
    )
    await callback.message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "buy_card")
async def process_buy_card(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id in PROCESSING_USERS:
        await callback.answer()
        return
    PROCESSING_USERS.add(user_id)

    try:
        player = get_player_data(user_id)
        
        # ТОЧНА ПЕРЕВІРКА: якщо коштів дійсно менше 10 TL
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

        # Списання грошей
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

        await callback.message.answer_photo(
            photo=card["image"],
            caption=caption,
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
