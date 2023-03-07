import asyncio
import datetime
import re
import time

from pyrogram import Client, types

from ..config import Config
from ..database import configDB, usersDB
from .broadcastHelper import send_broadcast_to_user
from .cache import Cache
from .logger import LOGGER

LOG = LOGGER(__name__)


async def check_pending(bot: Client):
    last_bc = await configDB.get_settings("LAST_BROADCAST")
    if last_bc and last_bc["completed"] == False:
        await handle_pending_broadcast(bot)
        LOG.info(f"--- Pending Broadcast completed ---")
    LOG.info(f"--- Pending tasks completed ---")


async def handle_pending_broadcast(bot: Client):
    last_bc = await configDB.get_settings("LAST_BROADCAST")
    users_list = await usersDB.get_pending_users(last_bc["id"])  # type: ignore
    Cache.CANCEL_BROADCAST = False

    start_time = time.time()
    total_users = await usersDB.total_users_count()
    global done, blocked, deleted, failed, success
    done = 0
    blocked = 0
    deleted = 0
    failed = 0
    success = 0

    is_copy = last_bc["settings"]["is_copy"]  # type: ignore
    is_pin = last_bc["settings"]["is_pin"]  # type: ignore

    sts = await bot.get_messages(last_bc["status"]["user_id"], last_bc["status"]["msg_id"])  # type: ignore

    if not sts.empty:  # type: ignore
        data = sts.text  # type: ignore
        reply_to = sts.id  # type: ignore
        count = re.findall(r"\d+", data)
        if len(count) == 7:
            counts = [int(k) for k in count]
            total_users, done, _, success, blocked, deleted, failed = counts
    else:
        reply_to = None

    to_broadcast = await bot.get_messages(Config.LOG_CHANNEL, last_bc["id"])  # type: ignore
    if to_broadcast.empty:  # type: ignore
        LOG.error("Pending BroadCast Cancelled because message was not found in LOG CHANNEL")
        await configDB.update_config(
            "LAST_BROADCAST",
            {
                "id": last_bc["id"],  # type: ignore
                "settings": {"is_copy": is_copy, "is_pin": is_pin},
                "status": {"user_id": sts.chat.id, "msg_id": sts.id},  # type: ignore
                "completed": True,
            },
        )

        return

    sts = await bot.send_message(
        last_bc["status"]["user_id"],  # type: ignore
        f"Broadcast in progress:\n\n"
        f"Total Users {total_users}\n"
        f"Completed: {done} / {total_users}\n"
        f"Success: {success}\n"
        f"Blocked: {blocked}\n"
        f"Deleted: {deleted}\n"
        f"Failed: {failed}",
        reply_to_message_id=reply_to,  # type: ignore
        reply_markup=types.InlineKeyboardMarkup(
            [[types.InlineKeyboardButton("Cancel", callback_data="broadcast_cancel")]]
        ),
    )

    await configDB.update_config(
        "LAST_BROADCAST",
        {
            "id": last_bc["id"],  # type: ignore
            "settings": {"is_copy": is_copy, "is_pin": is_pin},
            "status": {"user_id": sts.chat.id, "msg_id": sts.id},
            "completed": False,
        },
    )
    
    async def sendToUser(user):
        global done, blocked, deleted, failed, success
        try:
            if Cache.CANCEL_BROADCAST:
                await sts.edit(
                    f"Broadcast Cancelled:\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nBlocked: {blocked}\nDeleted: {deleted}\nFailed: {failed}"
                )
                Cache.CANCEL_BROADCAST = False
                await configDB.update_config(
                    "LAST_BROADCAST",
                    {
                        "id": last_bc["id"],  # type: ignore
                        "settings": {"is_copy": is_copy, "is_pin": is_pin},
                        "status": {"user_id": sts.chat.id, "msg_id": sts.id},
                        "completed": True,
                    },
                )
                return

            user_id = user["_id"]
            status_code, msg_id = await send_broadcast_to_user(int(user["id"]), to_broadcast, is_copy, is_pin)  # type: ignore
            if status_code == 200:
                success += 1
                await usersDB.broadcast_id(user_id, last_bc["id"])  # type: ignore
                await usersDB.update_broadcast_msg(user_id, msg_id)
            elif status_code == 404:
                deleted += 1
            elif status_code == 302:
                blocked += 1
                await usersDB.add_to_pending(user_id, last_bc["id"], {"is_copy": is_copy, "is_pin": is_pin})  # type: ignore
                await usersDB.update_blocked(user_id, True)
            elif status_code == 400:
                failed += 1

            done += 1
            await asyncio.sleep(1)
            if not done % 20:
                await sts.edit(
                    f"Broadcast in progress:\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nBlocked: {blocked}\nDeleted: {deleted}\nFailed: {failed}",
                    reply_markup=types.InlineKeyboardMarkup(
                        [[types.InlineKeyboardButton("Cancel", callback_data="broadcast_cancel")]]
                    ),
                )
        except Exception as e:
            LOG.exception(e)
    _tasks = []
    async for user in users_list:
        _tasks.append(sendToUser(user))
        if len(_tasks) > 500:
            await asyncio.gather(*_tasks)
            _tasks.clear()
            await asyncio.sleep(3)
    if _tasks:
        await asyncio.gather(*_tasks)
        
    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
    await configDB.update_config(
        "LAST_BROADCAST",
        {
            "id": last_bc["id"],  # type: ignore
            "settings": {"is_copy": is_copy, "is_pin": is_pin},
            "status": {"user_id": 626664225, "msg_id": sts.id},
            "completed": True,
        },
    )
    await sts.edit(
        f"Broadcast Completed:\nCompleted in {time_taken} seconds.\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nBlocked: {blocked}\nDeleted: {deleted}\nFailed: {failed}"
    )
