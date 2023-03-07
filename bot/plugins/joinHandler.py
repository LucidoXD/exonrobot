from datetime import datetime, timedelta

from pyrogram import types, enums

from bot import Bot, bot
import random
from apscheduler.jobstores.base import ConflictingIdError
from ..utils.chatSettings import getSettings
from ..utils.logger import LOGGER
from ..utils.utils import scheduler
from ..database import usersDB
from ..utils.parseUtils import (
    build_keyboard,
    escape,
    escape_invalid_curly_brackets,
    escape_markdown,
    mention_html,
    parse_button,
)

log = LOGGER(__name__)


async def escape_mentions_using_curly_brackets_wl(
    m: types.ChatJoinRequest,
    text: str,
    parse_words: list,
) -> str:
    teks = await escape_invalid_curly_brackets(text, parse_words)
    user = m.from_user
    await usersDB.handle_user(user.id, user.first_name)
    if teks:
        teks = teks.format(
            first=escape(user.first_name),
            last=escape(user.last_name or user.first_name),
            fullname=" ".join(
                [
                    escape(user.first_name),
                    escape(user.last_name),
                ]
                if user.last_name
                else [escape(user.first_name)],
            ),
            username=(
                "@" + (await escape_markdown(escape(user.username)))
                if user.username
                else (await (mention_html(escape(user.first_name), user.id)))
            ),
            mention=await (mention_html(escape(user.first_name), user.id)),
            chatname=escape(m.chat.title)
            if m.chat.type != enums.ChatType.PRIVATE
            else escape(user.first_name),
            id=user.id,
        )
    else:
        teks = ""

    return teks


async def sendMessage(update: types.ChatJoinRequest):
    settings_ = await getSettings(update.chat.id)
    settings = settings_["autoAccept"]
    text = settings["var"]["text"]

    parse_words = [
        "first",
        "last",
        "fullname",
        "username",
        "mention",
        "id",
        "chatname",
    ]
    parsed = await escape_mentions_using_curly_brackets_wl(update, text, parse_words)

    tek, button = await parse_button(parsed)
    button = await build_keyboard(button)
    button = types.InlineKeyboardMarkup(button) if button else None

    if "%%%" in tek:
        filter_reply = tek.split("%%%")
        teks = random.choice(filter_reply)
    else:
        teks = tek
    teks += "\n\n**Send /start to know more**"
    try:
        if settings["var"]["type"] == "text":
            await bot.send_message(
                update.chat.id,
                text=teks,
                reply_markup=button,
                disable_web_page_preview=True,
            )
        else:
            await bot.send_cached_media(
                update.chat.id,
                file_id=settings["var"]["file_id"],
                caption=teks,
                reply_markup=button,
            )
    except Exception as e:
        log.exception(e)


async def acceptRequest(update: types.ChatJoinRequest):
    try:
        await update.approve()
    except Exception as e:
        log.exception(e)


@Bot.on_chat_join_request()
async def handleRequests(bot: Bot, req: types.ChatJoinRequest):
    settings = await getSettings(req.chat.id, req.chat.title)
    if settings["autoAccept"]["status"]:
        delay = settings["autoAccept"]["delay"]
        await sendMessage(req)
        if delay > 0:
            try:
                scheduler.add_job(
                    acceptRequest,
                    "date",
                    [req.from_user.id, req.chat.id],
                    id=f"{req.chat.id}:{req.from_user.id}",
                    run_date=datetime.now() + timedelta(seconds=delay),
                    max_instances=5000000,
                    misfire_grace_time=600,
                )
            except ConflictingIdError:
                pass
        else:
            await acceptRequest(req)
    else:
        try:
            await bot.send_message(
                req.from_user.id,
                f"Thankyou for sending request to join chat [{req.chat.title}]"
                "\n\nYour request will be approved soon! \nHit /start to know more!",
            )
        except Exception as e:
            log.exception(e)
