import os
from dotenv import load_dotenv

load_dotenv("./.env")


class Config:
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    BOT_NAME = os.environ.get("BOT_NAME", "Bot")

    API_ID = int(os.environ.get("API_ID", ""))
    API_HASH = os.environ.get("API_HASH", "")

    DATABASE_URI = os.environ.get("DATABASE_URI", "")
    SESSION_NAME = os.environ.get("DATABASE_NAME", "TelegramBot")

    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0))
    SUDO_USERS = [int(user) for user in (os.environ.get("SUDO_USERS")).split()]
    SUPPORT_CHAT_URL = os.environ.get("SUPPORT_CHAT_URL", "https://t.me/")
