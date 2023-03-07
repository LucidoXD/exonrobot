from typing import Union

from pyrogram import handlers, types

from .client import PatchedClient


async def resolve_listener(
    client: PatchedClient,
    update: Union[types.CallbackQuery, types.Message, types.InlineQuery, types.ChosenInlineResult],
):
    if isinstance(update, types.CallbackQuery):
        if update.message:
            key = f"{update.message.chat.id}:{update.message.id}"
        elif update.inline_message_id:
            key = update.inline_message_id
        else:
            return
    elif isinstance(update, (types.ChosenInlineResult, types.InlineQuery)):
        key = str(update.from_user.id)
    else:
        key = str(update.chat.id)  # type: ignore

    listener = client.listeners.get(key)

    if listener and not listener["future"].done():  # type: ignore
        if callable(listener["filters"]):
            if not await listener["filters"](client, update):
                update.continue_propagation()
        listener["future"].set_result(update)  # type: ignore
        update.stop_propagation()
    else:
        if listener and listener["future"].done():  # type: ignore
            client.remove_listener(key, listener["future"])


class Client(PatchedClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def start(self, *args, **kwargs):
        self.add_handler(handlers.CallbackQueryHandler(resolve_listener), group=-1)
        self.add_handler(handlers.InlineQueryHandler(resolve_listener), group=-1)
        self.add_handler(handlers.ChosenInlineResultHandler(resolve_listener), group=-1)
        self.add_handler(handlers.MessageHandler(resolve_listener), group=-1)
        await super().start(*args, **kwargs)
