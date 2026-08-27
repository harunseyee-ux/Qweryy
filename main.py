from config import bot
from database import init_db
from handlers import register_handlers

# Inisialisasi DB
init_db()

# Register Seluruh Handlers
register_handlers(bot)

if __name__ == "__main__":
    print("🚀 Bot Store siap berjalan di Railway...")
    bot.infinity_polling(skip_pending=True)
