from pyrogram.types import Message
from pyrogram import enums

from bot import Bot
from ..database import usersDB
from .cache import Cache
from .utils import check_user
from .tools import getAdmins
from .delete import handleDelete


def is_banned(func):
    """decorator for banned users"""

    async def checker(bot: Bot, msg: Message):
        chat = msg.chat.id
        if msg.chat.type != enums.ChatType.PRIVATE:
            return await func(bot, msg)
        if chat in Cache.BANNED:
            reason = await usersDB.get_ban_status(msg.from_user.id)
            b_reason = reason.get("ban_reason")
            await msg.reply(f"You are banned to use me.\nReason - {b_reason}")
            await check_user(msg)
            msg.stop_propagation()
        else:
            await check_user(msg)
            return await func(bot, msg)

    return checker


def adminOnly(allow_anon: bool = False):
    """decorator for admin Only commands"""

    def wrapper(func):
        async def checker(bot: Bot, msg: Message):
            if msg.chat.type == enums.ChatType.PRIVATE:
                return await func(bot, msg)
            _, admins = await getAdmins(msg.chat.id)
            from_user = msg.from_user.id if msg.from_user else msg.sender_chat.id
            if not msg.from_user:
                if msg.sender_chat.id == msg.chat.id:
                    if allow_anon:
                        pass
                    else:
                        return await msg.reply(
                            "**ERROR**: This command cannot be used by anonymous admins!"
                        )
                else:
                    return await msg.reply("**ERROR**: This is an admin only command!")
            elif from_user in admins:
                pass
            else:
                return await msg.reply("**ERROR**: This is an admin only command!")

            return await func(bot, msg)

        return checker

    return wrapper


def delete(func):
    """decorator for deleting messages"""

    async def checker(bot: Bot, msg: Message):
        await handleDelete(msg)
        return await func(bot, msg)

    return checker


def groupsOnly(func):
    """decorator for  groups"""

    async def checker(bot: Bot, msg: Message):
        if msg.chat.type in [
            enums.ChatType.SUPERGROUP,
            enums.ChatType.GROUP,
            enums.ChatType.CHANNEL,
        ]:

            return await func(bot, msg)
        else:
            return await msg.reply(
                "**ERROR**: Unsupported Chat! This command is not meant to be used in private chat."
            )

    return checker
