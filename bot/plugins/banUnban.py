from bot import Bot
from pyrogram import filters
from pyrogram.types import Message

from ..config import Config
from ..database import usersDB
from ..utils.cache import Cache
from ..utils.logger import LOGGER

LOG = LOGGER(__name__)


@Bot.on_message(filters.user(Config.SUDO_USERS) & filters.command("ban"))  # type: ignore
async def ban_user(_, message: Message):
    if not len(message.command) > 1:
        return await message.reply("Specify a user")
    splitted = message.text.split()
    if len(splitted) > 2:
        _, user, reason = message.text.split(maxsplit=2)
    else:
        _, user = message.text.split(maxsplit=1)
        reason = "okDa"
    user = int(user)
    if user in Cache.BANNED:
        reason = await usersDB.get_ban_status(user)
        b_reason = reason.get("ban_reason")
        return await message.reply(f"This user is already banned\nReason - {b_reason}")
    await usersDB.ban_user(user, reason)
    Cache.BANNED.append(user)
    await message.reply(f"Successfully banned {user} for {reason}")
    LOG.info(f"Banned {user} for {reason}")


@Bot.on_message(filters.user(Config.SUDO_USERS) & filters.command("unban"))  # type: ignore
async def unban_user(_, message: Message):
    if not len(message.command) > 1:
        return await message.reply("Specify a user")
    _, user = message.text.split(maxsplit=1)
    user = int(user)
    if user not in Cache.BANNED:
        return await message.reply(f"This user is Not banned.")
    await usersDB.remove_ban(user)
    Cache.BANNED.remove(user)
    await message.reply(f"Successfully unbanned {user}.")
    LOG.info(f"Unbanned {user}")


@Bot.on_message(filters.user(Config.SUDO_USERS) & filters.command("check"))  # type: ignore
async def check_ban_user(_, message: Message):
    if not len(message.command) > 1:
        return await message.reply("Specify a user")
    _, user = message.text.split(maxsplit=1)
    user = int(user)
    if user in Cache.BANNED:
        reason = await usersDB.get_ban_status(user)
        b_reason = reason.get("ban_reason")
        return await message.reply(f"This user is banned for reason - {b_reason}")
    await message.reply("This user is not banned.")
