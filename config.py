import os
import telebot

# Telegram Configuration
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))
REQUIRED_CHANNEL = "@channelusername"  # Isi username channel join atau None jika tidak pakai

# Inisialisasi Bot Telegram
bot = telebot.TeleBot(TOKEN)

# Header Image Menu Utama (URL atau file_id Telegram)
HEADER_MENU_PHOTO = "https://picsum.photos/600/300"

# Database Configuration
DB_NAME = "store_bot.db"

# Memory State Management
user_data = {}

def get_state(chat_id):
    return user_data.get(chat_id, {}).get('state')

def set_state(chat_id, state):
    if chat_id not in user_data:
        user_data[chat_id] = {}
    user_data[chat_id]['state'] = state

def get_user_temp(chat_id, key):
    return user_data.get(chat_id, {}).get(key)

def set_user_temp(chat_id, key, value):
    if chat_id not in user_data:
        user_data[chat_id] = {}
    user_data[chat_id][key] = value
