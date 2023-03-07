import asyncio

from .database import usersDB

from bot import bot
from .utils.cache import Cache
from .utils.idle import idle
from .utils.logger import LOGGER
from .utils.utils import scheduler


async def main():
    await bot.start()
    Cache.BANNED = await usersDB.get_banned_users()
    LOGGER(__name__).info(f"Banned Users list updated {Cache.BANNED}")
    scheduler.start()
    LOGGER(__name__).info("Listening for updates from API..")
    await idle()
    await bot.stop()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
