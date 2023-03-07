import time
from datetime import datetime, timedelta

from apscheduler.jobstores.base import ConflictingIdError
from pyrogram import enums, types

from bot import bot

from .cache import Cache
from .chatSettings import getSettings
from .tools import getAdmins
from .utils import scheduler


async def handleDelete(msg: types.Message, del_in: int = 0):
    if msg.chat.type == enums.ChatType.PRIVATE:
        return
    config_ = await getSettings(msg.chat.id)
    config = config_["autoDelete"]
    if not config["status"]:
        return
    mode = config["var"]
    if mode == "text" and not msg.text:
        return
    elif mode == "media" and not msg.media:
        return

    time = max(config["delay"], del_in)
    return addToDelete(time, msg.chat.id, msg.id)


def addToDelete(time, chatID, msgID):
    """Add messages to scheduler"""
    deleteDate = datetime.now() + timedelta(seconds=time)
    try:
        scheduler.add_job(
            handleDeleteBot,
            "date",
            [chatID, msgID],
            id=f"{chatID}:{msgID}",
            run_date=deleteDate,
            max_instances=5000000,
            misfire_grace_time=600,
        )
    except ConflictingIdError:
        pass


async def handleDeleteBot(chatID: int, msgID: int):
    """
    delete messages by userBot
    """
    try:
        await bot.delete_messages(chatID, msgID)
    except Exception as e:
        await handleForbidden(chatID)


async def handleForbidden(chatID: int):
    """
    handle Forbidden messages [ old messages, non-admin rights]
    """

    settings = await getSettings(chatID)

    if chatID in Cache.FORBIDDEN:
        lastTime = Cache.FORBIDDEN[chatID]
    else:
        adminDict, adminList = await getAdmins(chatID)
        if (
            int(bot.me.id) not in adminList
            or not adminDict[bot.me.id].privileges.can_delete_messages
        ):
            await bot.send_message(
                chatID,
                "Iam not an admin here, Promote me as admin within 5 minutes, in order to delete messages!",
            )
            Cache.FORBIDDEN[chatID] = time.time()
        return
    if time.time() - lastTime > 300:
        if settings["paid"]:
            Cache.FORBIDDEN.pop(chatID)
            return
        await bot.send_message(
            chatID,
            "Leaving this group since Iam not having sufficient permissions to delete messages",
        )
        await bot.leave_chat(chatID)
        Cache.FORBIDDEN.pop(chatID)
