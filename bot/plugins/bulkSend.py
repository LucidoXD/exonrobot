import asyncio
from pyrogram import types, filters, enums
from bot import Bot
from ..database import conDB
from ..utils.tools import getCallBackQuery


@Bot.on_message(filters.private & filters.command("send"))
async def sendMessage(bot: Bot, msg: types.Message):
    con = await conDB.col.find_one({"userID": msg.from_user.id})
    if not con:
        return await msg.reply(
            "You do not have any chats connected!\nUse /connect to connect a chat."
        )

    chatList = []
    for chatType in ["group", "supergroup", "channel"]:
        chatList += con.get(chatType, [])
    toSend = []
    disableNotify = False
    isCopy = True

    def getButtons():
        buttons = []
        for chat in chatList:
            if chat["chatID"] in toSend:
                buttons.append(
                    [
                        types.InlineKeyboardButton(
                            f"✅ {chat['title']}", f"chat_{chat['chatID']}"
                        )
                    ]
                )
            else:
                buttons.append(
                    [
                        types.InlineKeyboardButton(
                            f"{chat['title']}", f"chat_{chat['chatID']}"
                        )
                    ]
                )
        buttons.append(
            [
                types.InlineKeyboardButton("Close", "close"),
                types.InlineKeyboardButton("Continue", "continue"),
            ]
        )
        return buttons

    _ask = await msg.reply(
        "Please select the chats that you want to send message and click continue.",
        reply_markup=types.InlineKeyboardMarkup(getButtons()),
    )
    while True:
        query = await getCallBackQuery(_ask)
        if not query:
            return
        elif query.data == "close":
            return await _ask.delete()
        elif query.data == "continue":
            if len(toSend) < 1:
                await query.answer("Select atleast one chat!", True)
                continue
            break
        else:
            chat = int(query.data.split("_")[1])
            if chat in toSend:
                toSend.remove(chat)

            else:
                toSend.append(chat)
            await _ask.edit_reply_markup(types.InlineKeyboardMarkup(getButtons()))
            continue

    await _ask.edit(
        f"Selected {len(toSend)} chats.\nNow Send the message that you want to send!"
    )

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
        isCopy = False
    await query.answer()

    await ask.edit(
        "Do you want to send this message silently?",
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
    if query.data == "yes":
        disableNotify = True
    await query.answer()

    res = await b_msg.copy(msg.chat.id) if isCopy else await b_msg.forward(msg.chat.id)

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
        await msg.reply("Cancelled Process")
        return
    sts = await ask.edit("Started sending..")

    async def _sendMessage(chatID):
        if isCopy:
            await b_msg.copy(chatID, disable_notification=disableNotify)
        else:
            await b_msg.forward(chatID, disable_notification=disableNotify)

    _tasks = [_sendMessage(chatID) for chatID in toSend]
    await asyncio.gather(*_tasks)
    return await sts.edit(f"Successfully posted to {len(toSend)} chats!")
