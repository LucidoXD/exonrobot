import asyncio

from pyrogram import enums, errors, filters, types

from bot import Bot

from ..client.client import ListenerCanceled
from ..database import conDB
from ..utils.chatSettings import getSettings, updateSettings
from ..utils.decorators import adminOnly
from ..utils.logger import LOGGER
from ..utils.parseUtils import get_message_data
from ..utils.tools import get_input

log = LOGGER(__name__)


def formatData(data):
    if isinstance(data, bool):
        if data == True:
            return "✅ Enabled"
        return "✖️ Disabled"
    return data


@Bot.on_message(filters.command("connect"))  # type: ignore
@adminOnly(False)
async def handleConnect(bot: Bot, msg: types.Message):
    chat: types.Chat
    if msg.chat.type == enums.ChatType.PRIVATE:
        if " " not in msg.text:
            while True:
                ask__ = await msg.reply(
                    "please forward a message from the channel with quotes.",
                    reply_markup=types.InlineKeyboardMarkup(
                        [
                            [
                                types.InlineKeyboardButton(
                                    "✖️ Cancel", callback_data=f"cancel_{msg.id}"
                                )
                            ]
                        ]
                    ),
                )
                try:
                    _msg = await bot.wait_for_message(msg.chat.id, timeout=600)
                except asyncio.TimeoutError:
                    return await ask__.edit(
                        "!ERROR: Exceeded maximum time.\nUse /connect again."
                    )
                except ListenerCanceled:
                    return await ask__.edit("Cancelled")
                if not _msg.forward_from_chat:
                    await msg.reply(
                        "invalid message!\nPlease forward a message from channel with quotes."
                    )
                    continue
                try:
                    await bot.get_chat_member(_msg.forward_from_chat.id, bot.me.id)
                except (errors.UserNotParticipant, errors.ChannelPrivate):
                    return await msg.reply(
                        f"Invalid Chat!\nMake sure @{bot.me.username} is admin in the channel."
                    )
                except Exception as e:
                    return await msg.reply(
                        f"Invalid Chat!\nMake sure @{bot.me.username} is admin in the channel."
                    )
                else:
                    chat = _msg.forward_from_chat
                    break
        else:
            chatID = msg.text.split(maxsplit=1)[1]
            try:
                chatID = int(chatID)
            except Exception:
                pass
            try:
                chat: types.Chat = await bot.get_chat(chatID)  # type: ignore
                await bot.get_chat_member(chatID, bot.me.id)
            except Exception as e:
                log.exception(e)
                return await msg.reply("Invalid Chat!")

    else:
        chat = msg.chat
    chatType = chat.type.value
    chats = [{"title": chat.title, "chatID": chat.id}]
    await conDB.col.update_one(
        {"userID": msg.from_user.id},
        {
            "$addToSet": {chatType: {"$each": chats}},
        },
        upsert=True,
    )  # type: ignore
    await msg.reply(f"Connected to **{chat.title}**")


@Bot.on_callback_query(filters.regex(r"^cancel"))
async def cancelCallBack(bot: Bot, query: types.CallbackQuery):
    if str(query.message.chat.id) in bot.listeners:
        bot.cancel_listener(str(query.message.chat.id))


@Bot.on_message(filters.command(["chats", "groups", "channels"]) & filters.private)
async def showConnections(bot: Bot, msg: types.Message):
    con = await conDB.col.find_one({"userID": msg.from_user.id})
    if not con:
        return await msg.reply(
            "You do not have any chats connected!\nUse /connect to connect a chat."
        )
    commands = {
        "/chats": {"types": ["group", "supergroup", "channel"], "name": "Chats"},
        "/groups": {"types": ["group", "supergroup"], "name": "Groups"},
        "/channels": {"types": ["channel"], "name": "Channels"},
    }
    buttons = []
    for chatType in commands[msg.text.lower().strip()]["types"]:
        chats = con.get(chatType, [])
        for chat in chats:
            buttons.append(
                [
                    types.InlineKeyboardButton(
                        chat["title"], callback_data=f"chat:{chat['chatID']}:main"
                    )
                ]
            )
    if not buttons:
        return await msg.reply(
            f"You do not have any {commands[msg.text.lower().strip()]['name']} connected!\nUse /connect to connect a chat."
        )
    await msg.reply(
        f"Available **{commands[msg.text.lower().strip()]['name']}** connections!\n",
        reply_markup=types.InlineKeyboardMarkup(buttons),
    )


@Bot.on_callback_query(filters.regex(r"^listchats"))
async def listChatCallBack(bot: Bot, query: types.CallbackQuery):
    con = await conDB.col.find_one({"userID": query.from_user.id})
    if not con:
        return await query.message.edit(
            "You do not have any chats connected!\nUse /connect to connect a chat."
        )

    buttons = []
    for chatType in ["group", "supergroup", "channel"]:
        chats = con.get(chatType, [])
        for chat in chats:
            buttons.append(
                [
                    types.InlineKeyboardButton(
                        chat["title"], callback_data=f"chat:{chat['chatID']}:main"
                    )
                ]
            )
    buttons.append([types.InlineKeyboardButton("✖️ Close", callback_data="close")])
    if not buttons:
        return await query.message.edit(
            f"You do not have any **chats** connected!\nUse /connect to connect a chat."
        )
    await query.message.edit(
        f"Available **chats** connections!\n",
        reply_markup=types.InlineKeyboardMarkup(buttons),
    )


@Bot.on_callback_query(filters.regex(r"^close"))
async def closeCallBack(bot: Bot, query: types.CallbackQuery):
    return await query.message.delete()


@Bot.on_callback_query(filters.regex(r"^chat"))
async def chatCallBack(bot: Bot, query: types.CallbackQuery):
    _, chatID, menu = query.data.split(":")  # type: ignore

    async def build():
        buttons = []
        for i in builder[menu]["subs"]:
            buttons.append(
                [
                    types.InlineKeyboardButton(
                        builder[menu]["subs"][i]["name"], f"chat:{chatID}:{i}"
                    )
                ]
            )
        buttons.append(
            [
                types.InlineKeyboardButton("🔙 Back", "listchats"),
                types.InlineKeyboardButton("✖️ Close", callback_data="close"),
            ]
        )
        await query.edit_message_text(
            "Choose the settings you want to toggle",
            reply_markup=types.InlineKeyboardMarkup(buttons),
        )

    def buildButtons(settings, menu):
        buttons = []
        for i in builder[menu]["subs"]:
            buttons.append(
                [
                    types.InlineKeyboardButton(
                        builder[menu]["subs"][i]["name"].format(
                            var=formatData(getKey(settings, i))
                        ),
                        f"chat:{chatID}:{i}",
                    )
                ]
            )
        return buttons

    async def subBuild():
        settings = await getSettings(int(chatID))
        buttons = buildButtons(settings, menu)
        buttons.append(
            [
                types.InlineKeyboardButton("🔙 Back", f"chat:{chatID}:main"),
                types.InlineKeyboardButton("✖️ Close", callback_data="close"),
            ]
        )
        await query.edit_message_text(
            "Choose the settings you want to toggle",
            reply_markup=types.InlineKeyboardMarkup(buttons),
        )

    async def updateBool():
        buttons = []
        settings = await getSettings(int(chatID))
        main, sub = menu.split("_")
        settings_ = await updateSettings(
            int(chatID), main, not getKey(settings, menu), sub
        )
        buttons = buildButtons(settings_, main)
        buttons.append(
            [
                types.InlineKeyboardButton("🔙 Back", f"chat:{chatID}:{main}"),
                types.InlineKeyboardButton("✖️ Close", callback_data="close"),
            ]
        )
        await query.edit_message_text(
            "Choose the settings you want to toggle",
            reply_markup=types.InlineKeyboardMarkup(buttons),
        )

    async def handleInputTime():
        buttons = []
        main, sub = menu.split("_")
        _msg = await query.message.reply("Send Delay time in seconds")
        newTime = await get_input(_msg)
        if not newTime:
            return
        try:
            newTime = int(newTime)
        except Exception as e:
            return await _msg.reply(
                "Invalid Input!\nExpected a number, received {newTime}"
            )
        settings_ = await updateSettings(int(chatID), main, newTime, sub)
        buttons = buildButtons(settings_, main)
        buttons.append([types.InlineKeyboardButton("🔙 Back", f"chat:{chatID}:{main}")])
        await query.message.reply(
            "Choose the settings you want to toggle",
            reply_markup=types.InlineKeyboardMarkup(buttons),
        )

    async def handleVarSettings():
        buttons = []
        main, sub = menu.split("_")
        settings = await getSettings(int(chatID))
        _msg = await query.message.reply(
            "send new welcome message to be sent when people requests to join this channel."
            f"\n\nCurrent Message: {settings['autoAccept']['var']}"
        )
        try:
            newWelcome = await bot.wait_for_message(query.message.chat.id, timeout=600)
        except asyncio.TimeoutError:
            return
        text, msg_type, file_id = await get_message_data(newWelcome)
        newWelcome = await get_input(_msg)
        if not newWelcome:
            return
        settings_ = await updateSettings(
            int(chatID), main, {"type": msg_type, "text": text, "file_id": file_id}, sub
        )
        buttons = buildButtons(settings_, main)
        buttons.append(
            [
                types.InlineKeyboardButton("🔙 Back", f"chat:{chatID}:{main}"),
                types.InlineKeyboardButton("✖️ Close", callback_data="close"),
            ]
        )
        await query.message.reply(f"New Welcome Message Saved")
        await query.message.reply(
            "Choose the settings you want to toggle",
            reply_markup=types.InlineKeyboardMarkup(buttons),
        )

    async def handleDeleteMode():
        buttons = []
        main, sub = menu.split("_")
        settings = await getSettings(int(chatID))
        current = settings["autoDelete"]["var"]
        _next = {"media": "text", "text": "all", "all": "media"}
        settings_ = await updateSettings(int(chatID), main, _next[current], sub)
        buttons = buildButtons(settings_, main)
        buttons.append(
            [
                types.InlineKeyboardButton("🔙 Back", f"chat:{chatID}:{main}"),
                types.InlineKeyboardButton("✖️ Close", callback_data="close"),
            ]
        )
        await query.edit_message_text(
            "Choose the settings you want to toggle",
            reply_markup=types.InlineKeyboardMarkup(buttons),
        )

    async def handleDeleteConnection():
        if "yes" in menu:
            chat = await conDB.col.find_one({"userID": query.from_user.id})
            for chatType in ["group", "supergroup", "channel"]:
                chats = chat.get(chatType, [])
                for chat in chats:
                    if chat["chatID"] == int(chatID):
                        await conDB.col.update_one(
                            {"userID": query.from_user.id}, {"$pull": {chatType: chat}}
                        )

                        await query.answer("Disconnected", True)
                        return await listChatCallBack(bot, query)
        else:
            await query.answer("Cancelled", True)
            return await listChatCallBack(bot, query)

    async def handleDeleteConfirm():
        buttons = [
            [
                types.InlineKeyboardButton(
                    "Yes", callback_data=f"chat:{chatID}:remove_yes"
                ),
                types.InlineKeyboardButton("No", f"chat:{chatID}:remove_no"),
            ]
        ]
        buttons.append(
            [
                types.InlineKeyboardButton("🔙 Back", f"chat:{chatID}:main"),
                types.InlineKeyboardButton("✖️ Close", callback_data="close"),
            ]
        )
        await query.edit_message_text(
            "Choose the settings you want to toggle",
            reply_markup=types.InlineKeyboardMarkup(buttons),
        )

    builder = {
        "main": {
            "func": build,
            "subs": {
                "autoAccept": {"name": "Auto-Accept", "func": ""},
                "autoDelete": {"name": "Auto-Delete", "func": ""},
                "remove": {"name": "Remove Connection", "func": ""},
            },
        },
        "autoAccept": {
            "func": subBuild,
            "subs": {
                "autoAccept_status": {"name": "Status: {var}", "func": updateBool},
                "autoAccept_delay": {"name": "Delay: {var}", "func": handleInputTime},
                "autoAccept_var": {
                    "name": "Welcome Message",
                    "func": handleVarSettings,
                },
            },
        },
        "autoDelete": {
            "func": subBuild,
            "subs": {
                "autoDelete_status": {"name": "Status: {var}", "func": updateBool},
                "autoDelete_delay": {"name": "Time: {var}", "func": handleInputTime},
                "autoDelete_var": {"name": "Type: {var}", "func": handleDeleteMode},
            },
        },
        "remove": {
            "func": handleDeleteConfirm,
            "subs": {
                "remove_yes": {"name": "Yes", "func": handleDeleteConnection},
                "remove_no": {"name": "No", "func": handleDeleteConnection},
            },
        },
    }

    def getFunc():
        data = builder
        for i in menu.split("_"):
            data = data[i] if i in builder.keys() else data["subs"][menu]
        return data["func"]

    def getKey(settings: dict, key: str):
        data = settings.copy()
        for i in key.split("_"):
            data = data[i]
        return data

    await getFunc()()
