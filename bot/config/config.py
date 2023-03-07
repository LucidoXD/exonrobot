import os
from dotenv import load_dotenv

load_dotenv("./.env")


class Config:
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "1739231223:AAGBcJ3vgHOW_0vvVnoYB61zNgz9hx9vWn0")
    BOT_NAME = os.environ.get("BOT_NAME", "Bot")

    API_ID = int(os.environ.get("API_ID", "27589257"))
    API_HASH = os.environ.get("API_HASH", "0af78b04b48361bc117fa4e06d6d2292")

    DATABASE_URI = os.environ.get("DATABASE_URI", "mongodb+srv://kk:kk@cluster0.qgpzaa7.mongodb.net/?retryWrites=true&w=majority")
    SESSION_NAME = os.environ.get("DATABASE_NAME", "TelegramBot")

    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0))
    SUDO_USERS = [int(user) for user in (os.environ.get("SUDO_USERS")).split()]
    SUPPORT_CHAT_URL = os.environ.get("SUPPORT_CHAT_URL", "https://t.me/drewnotfound")
