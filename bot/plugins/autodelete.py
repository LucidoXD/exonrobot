from bot import Bot
from pyrogram import filters, types, enums
from ..utils.decorators import delete, groupsOnly, adminOnly


@Bot.on_message(filters.command("settings"))
@groupsOnly
@adminOnly(True)
async def handleSettings(bot: Bot, msg: types.Message):
    await msg.reply("Use /connect and set settings in PM")


@Bot.on_message(group=-2)
@delete
async def handleMessage(bot: Bot, msg: types.Message):
    msg.continue_propagation()
