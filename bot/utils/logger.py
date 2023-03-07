from logging.handlers import RotatingFileHandler
import logging
import os

if not os.path.exists("./bot/logs"):
    os.mkdir("./bot/logs")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler("./bot/logs/botlogs.log", maxBytes=500000, backupCount=10),
        logging.StreamHandler(),
    ],
)


logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("aiohttp.access").setLevel(logging.ERROR)


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
