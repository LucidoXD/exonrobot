from pyrogram import enums, filters, types

from bot import Bot

from ..config import Config
from ..utils.decorators import is_banned

START_TEXT = """Hey {mention} 👋
Iam A Feature-filled Channel / Group Management Bot
I can do multiple tasks for you which includes;

1. Auto Accepting chat-join requests __[ with customized welcome message and delay]__
2. Auto-Deleting messages after specified intervals __[ with custom filters for media and text]__
3. Channel-Broadcasting and may more... __[sending messages to connected chats at a time.]__

Use /help to explore all the functions!
"""

HELP_TEXT = """
**Available Commands and Explanation**

>> /start - __To See info about the bot__
>> /help - __To see this message.__
>> /connect - __To connect a channel / group for further settings.__
>> /chats - __Lists the available connected chats.__
>> /send - __To send messages to connected chats together.__

**Commands For Groups**
>> /welcome <on / off> -  __To set welcome message on / off__
>> /setwelcome [as reply to message]- __To set up a new welcome message [check advanced usage to know about formatting]__
>> /goodbye <on / off> - __To set goodbye message on / off__
>> /setgoodbye [as reply to message] - __To set a goodbye message when a user leaves the group [check advanced usage to know about formatting].__

**Auto-Accept Settings**
1. First you have to connect the desired channel / group using /connect.
2. Once chat is connected with your PM, use /chats to view the connected chats.
3. Click on any chat to set-up auto-accept and auto-delete.
4. You can set a delay for accepting the requests, which means users will be accepted only after the set delay.
5. You can also set-up a welcome message, which will be sent to the user, once he send request to join the channel / group.

**Auto-Delete Settings**
1. Connect the chat same as above
2. Use /chats to enter into `Auto-Delete` settings for specific chats.
3. You can turn on / off auto delete using the status button.
4. You can set delay for deleting the message 
5. You can also set `type` of messages to be deleted [text, media or all]
"""

FORMAT = """
<b>Markdown Formatting</b>
You can format your message using <b>bold</b>, <i>italic</i>, <u>underline</u>, <strike>strike</strike> and much more. Go ahead and experiment!
<b>Note</b>: It supports telegram user based formatting as well as html and markdown formattings.

<b>Supported markdown</b>:
- <code>`code words`</code>: Backticks are used for monospace fonts. Shows as: <code>code words</code>.
- <code>__italic__</code>: Underscores are used for italic fonts. Shows as: <i>italic words</i>.
- <code>**bold**</code>: Asterisks are used for bold fonts. Shows as: <b>bold words</b>.
- <code>```pre```</code>: To make the formatter ignore other formatting characters inside the text formatted with '```', like: <code>**bold** | *bold*</code>.
- <code>--underline--</code>: To make text <u>underline</u>.
- <code>~~strike~~</code>: Tildes are used for strikethrough. Shows as: <strike>strike</strike>.
- <code>||spoiler||</code>: Double vertical bars are used for spoilers. Shows as: <spoiler>Spoiler</spoiler>.
- <code>[hyperlink](example.com)</code>: This is the formatting used for hyperlinks. Shows as: <a href="https://example.com/">hyperlink</a>.
- <code>[My Button](buttonurl://example.com)</code>: This is the formatting used for creating buttons. This example will create a button named "My button" which opens <code>example.com</code> when clicked.
If you would like to send buttons on the same row, use the <code>:same</code> formatting.
<b>Example:</b>
<code>[button 1](buttonurl:example.com)</code>
<code>[button 2](buttonurl://example.com:same)</code>
<code>[button 3](buttonurl://example.com)</code>
This will show button 1 and 2 on the same line, while 3 will be underneath.


<b>Fillings</b>
You can also customise the contents of your message with contextual data. For example, you could mention a user by name in the welcome message, or mention them in a filter!
You can use these to mention a user in notes too!
<b>Supported fillings:</b>
- <code>{first}</code>: The user's first name.
- <code>{last}</code>: The user's last name.
- <code>{fullname}</code>: The user's full name.
- <code>{username}</code>: The user's username. If they don't have one, mentions the user instead.
- <code>{mention}</code>: Mentions the user with their firstname.
- <code>{id}</code>: The user's ID.
- <code>{chatname}</code>: The chat's name.
"""


@Bot.on_message(filters.command("start") & filters.incoming)  # type: ignore
@is_banned
async def start_handler(_: Bot, msg: types.Message):
    await msg.reply(
        START_TEXT.format(mention=msg.from_user.mention),
        reply_markup=types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton("🔖 Help", callback_data=f"help"),
                    types.InlineKeyboardButton(
                        "🔗 Support", url=Config.SUPPORT_CHAT_URL
                    ),
                ]
            ]
        ),
        disable_web_page_preview=True,
    )


@Bot.on_callback_query(filters.regex("help"))  # type: ignore
async def help_handler_query(_: Bot, query: types.CallbackQuery):
    await query.answer()
    await query.edit_message_text(
        HELP_TEXT,
        reply_markup=types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton("◀️ Back", callback_data="back_home"),
                    types.InlineKeyboardButton("📘 Advanced Help", "advHelp"),
                ]
            ]
        ),
    )


@Bot.on_callback_query(filters.regex("advHelp"))  # type: ignore
async def adv_handler_query(_: Bot, query: types.CallbackQuery):
    await query.edit_message_text(
        FORMAT,
        reply_markup=types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton("◀️ Back", callback_data="help"),
                ]
            ]
        ),
        parse_mode=enums.ParseMode.HTML,
    )


@Bot.on_callback_query(filters.regex("back"))  # type: ignore
async def home_handler(_: Bot, query: types.CallbackQuery):
    await query.answer()
    await query.edit_message_text(
        START_TEXT.format(mention=query.from_user.mention),
        reply_markup=types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton("🔖 Help", callback_data=f"help"),
                    types.InlineKeyboardButton(
                        "🔗 Support", url=Config.SUPPORT_CHAT_URL
                    ),
                ]
            ]
        ),
        disable_web_page_preview=True,
    )


@Bot.on_message(filters.command("help") & filters.incoming)  # type: ignore
@is_banned
async def help_handler(_: Bot, msg: types.Message):
    await msg.reply(
        HELP_TEXT,
        reply_markup=types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton("📘 Advanced Help", "advHelp"),
                    types.InlineKeyboardButton(
                        "🔗 Support", url=Config.SUPPORT_CHAT_URL
                    ),
                ]
            ]
        ),
    )
