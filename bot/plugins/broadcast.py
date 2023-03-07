import asyncio
import logging
import datetime
import time

from bot import Bot
from pyrogram import filters, types

from ..config import Config
from ..database import configDB, usersDB
from ..utils.broadcastHelper import send_broadcast_to_user
from ..utils.cache import Cache
from ..utils.logger import LOGGER

LOG: logging.Logger = LOGGER(__name__)


@Bot.on_message(filters.command("broadcastusr") & filters.user(Config.SUDO_USERS))  # type: ignore
async def broadcast_handler(bot: Bot, msg: types.Message):
    is_copy = True
    is_pin = False

    await msg.reply("Alright Now send Photo / Video / Whatever you want.")
    b_msg = await bot.wait_for_message(msg.chat.id, timeout=600)
    if b_msg:
        if b_msg.text and b_msg.text == "/cancel":
            return await msg.reply("Cancelled")

    ask = await bot.send_message(
        msg.chat.id,
        "How do you want the message send as?",
        reply_markup=types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton("Forward", callback_data="forward"),
                    types.InlineKeyboardButton("Copy", callback_data="copy"),
                ]
            ]
        ),
    )
    query = await bot.wait_for_callback_query(msg.chat.id, ask.id)
    if query.data == "forward":
        is_copy = False
    await query.answer()
    to_broadcast = (
        await b_msg.copy(Config.LOG_CHANNEL)
        if is_copy
        else await b_msg.forward(Config.LOG_CHANNEL)
    )
    await ask.edit(
        "Do you want to pin the message?",
        reply_markup=types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton("Yes", callback_data="pin"),
                    types.InlineKeyboardButton("No", callback_data="no"),
                ]
            ]
        ),
    )
    query = await bot.wait_for_callback_query(msg.chat.id, ask.id)
    if query.data == "pin":
        is_pin = True
    await query.answer()

    await send_broadcast_to_user(msg.chat.id, to_broadcast, is_copy, is_pin)  # type: ignore

    ask = await msg.reply(
        "Here is the sample , Do you wish to Proceed?",
        reply_markup=types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton("Yes", callback_data="yes"),
                    types.InlineKeyboardButton("No", callback_data="no"),
                ]
            ]
        ),
    )

    query = await bot.wait_for_callback_query(msg.chat.id, ask.id)
    await query.answer()
    if query.data == "no":
        await msg.reply("Cancelled Broadcast Process")
        return

    sts = await msg.reply_text(
        text="Broadcasting your messages...",
        reply_markup=types.InlineKeyboardMarkup(
            [[types.InlineKeyboardButton("Cancel", callback_data="broadcast_cancel")]]
        ),
    )
    start_time = time.time()
    total_users = await usersDB.total_users_count()
    global done, blocked, deleted, failed, success
    done = 0
    blocked = 0
    deleted = 0
    failed = 0
    success = 0
    users_list = await usersDB.get_all_users()
    Cache.CANCEL_BROADCAST = False

    await configDB.update_config(
        "LAST_BROADCAST",
        {
            "id": to_broadcast.id,  # type: ignore
            "settings": {"is_copy": is_copy, "is_pin": is_pin},
            "status": {"user_id": 626664225, "msg_id": sts.id},
            "completed": False,
        },
    )

    async def sendToUser(user: dict):
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
                        "id": to_broadcast.id,  # type: ignore
                        "settings": {"is_copy": is_copy, "is_pin": is_pin},
                        "status": {"user_id": 626664225, "msg_id": sts.id},
                        "completed": True,
                    },
                )
                return

            user_id = int(user["_id"])
            status_code, msg_id = await send_broadcast_to_user(int(user["_id"]), to_broadcast, is_copy, is_pin)  # type: ignore
            if status_code == 200:
                success += 1
                await usersDB.broadcast_id(user_id, to_broadcast.id)  # type: ignore
                await usersDB.update_broadcast_msg(user_id, msg_id)
            elif status_code == 404:
                deleted += 1
            elif status_code == 302:
                blocked += 1
                await usersDB.add_to_pending(user_id, to_broadcast.id, {"is_copy": is_copy, "is_pin": is_pin})  # type: ignore
                await usersDB.update_blocked(user_id, True)
            elif status_code == 400:
                failed += 1

            done += 1
            # await asyncio.sleep(1)
            if not done % 20:
                await sts.edit(
                    f"Broadcast in progress:\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nBlocked: {blocked}\nDeleted: {deleted}\nFailed: {failed}",
                    reply_markup=types.InlineKeyboardMarkup(
                        [
                            [
                                types.InlineKeyboardButton(
                                    "Cancel", callback_data="broadcast_cancel"
                                )
                            ]
                        ]
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
            "id": to_broadcast.id,  # type: ignore
            "settings": {"is_copy": is_copy, "is_pin": is_pin},
            "status": {"user_id": 626664225, "msg_id": sts.id},
            "completed": True,
        },
    )
    await sts.edit(
        f"Broadcast Completed:\nCompleted in {time_taken} seconds.\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nBlocked: {blocked}\nDeleted: {deleted}\nFailed: {failed}"
    )


@Bot.on_callback_query(filters.regex(r"^broadcast_cancel") & filters.user(Config.SUDO_USERS))  # type: ignore
async def cancel_broadcast(_: Bot, query: types.CallbackQuery):
    await query.answer("Canceling...")
    Cache.CANCEL_BROADCAST = True


@Bot.on_message(filters.command("stats") & filters.user(626664225))  # type: ignore
async def stats_users(_: Bot, msg: types.Message):
    count = await usersDB.total_users_count()
    await msg.reply(f"Total Users {count}")
