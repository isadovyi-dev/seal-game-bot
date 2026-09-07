import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# Токен твого бота
TOKEN = "8072842801:AAHgOyzmksuZrYOGnoSSYmsgVEOKUxklMcA"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ТВОЇ КОМАНДИ БОТА ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привіт! Я працюю 24/7 і більше не засинаю! 🦭")

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ТА CRON-JOB ---
async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render передає порт через змінну PORT
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- ГОЛОВНИЙ ЗАПУСК ---
async def main():
    await start_web_server()
    print("Веб-сервер запущено!")
    print("Запускаємо бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
