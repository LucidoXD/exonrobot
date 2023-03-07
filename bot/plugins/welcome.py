import random

from pyrogram import Client, enums, filters, types

from ..utils.chatSettings import getSettings, updateSettings
from ..utils.decorators import adminOnly, groupsOnly
from ..utils.logger import LOGGER
from ..utils.parseUtils import (
    build_keyboard,
    escape,
    escape_invalid_curly_brackets,
    escape_markdown,
    get_message_data,
    mention_html,
    parse_button,
)

LOG = LOGGER("greetings")


async def join_chat_member_update_filter(m: types.ChatMemberUpdated):
    if m.new_chat_member:
        ncm = m.new_chat_member
        ocm = m.old_chat_member
        if (
            ocm
            and ncm.status == enums.ChatMemberStatus.RESTRICTED
            and ocm.is_member is False
        ):
            return ncm.is_member
        elif ncm.status in [
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.MEMBER,
            enums.ChatMemberStatus.OWNER,
        ]:
            return bool(not ocm or ocm.is_member is False)
    return False


async def left_chat_member_update_filter(m: types.ChatMemberUpdated):
    ncm = m.new_chat_member
    ocm = m.old_chat_member
    if (
        ncm
        and ocm
        and ncm.status
        in [enums.ChatMemberStatus.RESTRICTED, enums.ChatMemberStatus.BANNED]
    ):
        return bool(ocm.is_member is not False and not ncm.is_member)
    return bool(
        not ncm
        and ocm.status
        not in [enums.ChatMemberStatus.RESTRICTED, enums.ChatMemberStatus.BANNED]
    )


async def escape_mentions_using_curly_brackets_wl(
    m: types.ChatMemberUpdated,
    n: bool,
    text: str,
    parse_words: list,
) -> str:
    teks = await escape_invalid_curly_brackets(text, parse_words)
    if n:
        user = m.new_chat_member.user if m.new_chat_member else m.from_user
    else:
        user = m.old_chat_member.user if m.old_chat_member else m.from_user
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


@Client.on_message(filters.command(["setwelcome", "setgoodbye"]))
@groupsOnly
async def save_greetings(_, m: types.Message):

    db_settings = await getSettings(m.chat.id)

    settings = {"/setwelcome": "welcome_settings", "/setgoodbye": "goodbye_settings"}
    command = m.text.split()[0].lower()
    req_settings = db_settings[settings[command]]

    if m and not m.from_user:
        return
    args = m.text.split(None, 1)

    if not (m.reply_to_message and m.reply_to_message.text) and len(m.command) == 0:
        await m.reply_text(
            "Error: There is no text in here! and only text with buttons are supported currently !",
        )
        return
    text, msg_type, file_id = await get_message_data(m)

    if not m.reply_to_message and msg_type == "text" and len(m.command) < 2:
        await m.reply_text(f"<code>{m.text}</code>\n\nError: There is no data in here!")
        return

    if not text and not msg_type:
        await m.reply_text(
            "Please provide some data!",
        )
        return

    if not msg_type:
        await m.reply_text("Please provide some data for this to reply with!")
        return

    if (
        (msg_type == "text" and len(text) >= 4096)
        or msg_type != "text"
        and len(text) >= 1024
    ):
        await m.reply_text(
            "Word limit exceed !!",
        )
        return

    req_settings["message"] = {"type": msg_type, "text": text, "file_id": file_id}
    await updateSettings(m.chat.id, settings[command], req_settings)
    await m.reply_text("Saved settings!")


@Client.on_message(filters.command(["resetgoodbye", "resetwelcome"]))
@groupsOnly
@adminOnly(True)
async def reset_greetings(_, m: types.Message):

    db_settings = await getSettings(m.chat.id)
    settings = {
        "/resetwelcome": "welcome_settings",
        "/resetgoodbye": "goodbye_settings",
    }
    command = m.text.split()[0].lower()
    req_settings = db_settings[settings[command]]
    default = {
        "/resetwelcome": "Sad to see you leaving {first}.\nTake Care!",
        "/resetgoodbye": "Hey {first}, welcome to {chatname}!",
    }

    req_settings["message"] = {
        "type": "text",
        "text": default[command],
        "file_id": None,
    }

    await updateSettings(m.chat.id, settings[command], req_settings)
    await m.reply_text("Settings reverted to default!")


@Client.on_chat_member_updated(filters.group, group=5)
async def member_has_joined(bot: Client, update: types.ChatMemberUpdated):
    db_settings = await getSettings(update.chat.id)
    if await join_chat_member_update_filter(update):
        req = "welcome_settings"
        user = update.new_chat_member.user or update.old_chat_member.user
    elif await left_chat_member_update_filter(update):
        req = "goodbye_settings"
        user = update.old_chat_member.user or update.new_chat_member.user
    else:
        return

    if user.is_bot:
        return  # ignore bots

    greetings_settings = db_settings[req]
    text = greetings_settings["message"]["text"]
    if not greetings_settings["status"]:
        return
    parse_words = [
        "first",
        "last",
        "fullname",
        "username",
        "mention",
        "id",
        "chatname",
    ]
    parsed = await escape_mentions_using_curly_brackets_wl(
        update, True, text, parse_words
    )

    tek, button = await parse_button(parsed)
    button = await build_keyboard(button)
    button = types.InlineKeyboardMarkup(button) if button else None

    if "%%%" in tek:
        filter_reply = tek.split("%%%")
        teks = random.choice(filter_reply)
    else:
        teks = tek
    if greetings_settings["clean"]:
        last = greetings_settings["last"]
        if last:
            try:
                await bot.delete_messages(update.chat.id, last)
            except Exception as e:
                pass
    try:
        if greetings_settings["message"]["type"] == "text":
            new = await bot.send_message(
                update.chat.id,
                text=teks,
                reply_markup=button,
                disable_web_page_preview=True,
            )
        else:
            new = await bot.send_cached_media(
                update.chat.id,
                file_id=greetings_settings["message"]["file_id"],
                caption=teks,
                reply_markup=button,
            )
        greetings_settings["last"] = new.id
        await updateSettings(update.chat.id, req, greetings_settings)
    except Exception as e:
        LOG.error(e)
        return


@Client.on_message(filters.command(["welcome", "goodbye"]))
@groupsOnly
@adminOnly(True)
async def enable_greets(bot: Client, m: types.Message):
    db_settings = await getSettings(m.chat.id)
    settings = {"/welcome": "welcome_settings", "/goodbye": "goodbye_settings"}
    command = m.text.split()[0].lower()
    req_settings = db_settings[settings[command]]

    args = m.text.split(" ", 1)

    if len(args) >= 2:

        if args[1].lower() == "on":
            req_settings["status"] = True
            await m.reply_text("Turned on!")
        elif args[1].lower() == "off":
            req_settings["status"] = False
            await m.reply_text("Turned Off!")
        else:
            await m.reply_text("Provide on / off")
            return
        await updateSettings(m.chat.id, settings[command], req_settings)
    else:
        return await m.reply("use either on / off")
