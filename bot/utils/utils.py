import traceback

import tzlocal
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pymongo import MongoClient
from pyrogram import enums, errors, filters, types
from pyrogram.types import Message

from bot import Bot, bot

from ..config import Config
from ..database import usersDB
from .broadcastHelper import send_broadcast_to_user
from .cache import Cache
from .logger import LOGGER

LOG_TEXT_USER = (
    "#USER\n**New User**\n\nName: [{}](tg://user?id={})\nUser_ID: <code>{}</code>"
)


LOG = LOGGER(__name__)


scheduler = AsyncIOScheduler(
    jobstores={
        "default": MongoDBJobStore(
            client=MongoClient(Config.DATABASE_URI),
            database=Config.SESSION_NAME,
            collection="asyncJobs",
        )
    },
    timezone=str(tzlocal.get_localzone()),
)


async def check_user(message: Message):
    if message.chat.type == enums.ChatType.PRIVATE:
        name = message.from_user.first_name
    elif message.chat.type in [enums.ChatType.SUPERGROUP, enums.ChatType.CHANNEL]:
        name = message.chat.title
    else:
        name = ""
    is_new = await usersDB.handle_user(message.chat.id, name)
    if is_new:
        await bot.send_message(
            Config.LOG_CHANNEL,
            LOG_TEXT_USER.format(name, message.chat.id, message.chat.id),
        )
        LOG.info(
            f"newUser - {message.from_user.first_name}  ----- {message.from_user.id}"
        )
    else:
        user = await usersDB.col.find_one({"_id": message.chat.id})  # type: ignore
        if user.get("blocked"):
            pending = user.get("pending_broadcast")
            if pending:
                msg = await bot.get_messages(Config.LOG_CHANNEL, pending)
                if msg:
                    settings = user.get("broadcast_info", {})
                    is_copy = settings.get("is_copy", True)
                    is_pin = settings.get("is_pin", False)

                    await message.reply(
                        "Nice to see you again.\nYou missed an update from developer because you blocked me for a while :(\nHere is it"
                    )
                    _, msg_id = await send_broadcast_to_user(message.chat.id, msg, is_copy, is_pin)  # type: ignore
                    await usersDB.broadcast_id(message.chat.id, pending)
                    await usersDB.update_broadcast_msg(message.chat.id, msg_id)
                await usersDB.update_blocked(message.chat.id, False)
                await usersDB.remove_pending(message.chat.id)


async def checkChatMember(bot: Bot, message: types.Message):
    user = message.from_user.id
    try:
        member = await bot.get_chat_member("subin_works", user)
    except errors.UserNotParticipant:
        btn = types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton(
                        "Join Update Channel", url="https://t.me/subin_works"
                    )
                ]
            ]
        )
        await message.reply(
            "Join Update Channel to use me",
            reply_markup=btn,
        )
        return False
    else:
        if member.status in [enums.ChatMemberStatus.BANNED]:
            await message.reply("okDa")
            return False
        return True


async def log(text: str, msg: types.Message, error: bool = False):
    out = f"USER: {msg.from_user.mention} [`{msg.from_user.id}`]\n\n" + text
    if error:
        trace = traceback.format_exc()
        out += f"#ERROR\n\n```python\n{trace}```"
    await bot.send_message(Config.LOG_CHANNEL, out, disable_web_page_preview=True)


async def handle_admin_update(group: int, member: types.ChatMember):
    if group in Cache.ADMINS:
        admins, admins_list = Cache.ADMINS[group]["admins"], Cache.ADMINS[group]["list"]
        if member.status in [
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER,
        ]:
            admins[member.user.id] = member  # type: ignore
            if member.user.id not in admins_list:  # type: ignore
                admins_list.append(member.user.id)  # type: ignore

        elif member.status in [
            enums.ChatMemberStatus.MEMBER,
            enums.ChatMemberStatus.BANNED,
            enums.ChatMemberStatus.RESTRICTED,
        ]:
            if member.user.id in admins_list:  # type: ignore

                admins_list.remove(member.user.id)  # type: ignore
                admins.pop(member.user.id)  # type: ignore
        Cache.ADMINS[group] = {
            "admins": admins,
            "list": admins_list,
            "time": Cache.ADMINS[group]["time"],
        }
