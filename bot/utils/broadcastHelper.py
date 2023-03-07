from .logger import LOGGER
from pyrogram import types, errors
import asyncio
from ..database import usersDB

log = LOGGER(__name__)


async def send_broadcast_to_user(
    user_id: int, message: types.Message, is_copy: bool = True, pin_msg: bool = False
):
    try:
        if is_copy:
            msg = await message.copy(chat_id=user_id)
        else:
            msg = await message.forward(user_id)
        if pin_msg:
            await msg.pin(both_sides=True)  # type: ignore
        LOGGER(__name__).info(f"Broadcast Sent to {user_id}")
        return 200, msg.id  # type: ignore
    except errors.FloodWait as e:
        LOGGER(__name__).warn(f"FloodWait of {e.value} seconds while broadcasting.")
        await asyncio.sleep(e.value)  # type: ignore
        return await send_broadcast_to_user(user_id, message, is_copy, pin_msg)
    except errors.InputUserDeactivated:
        await usersDB.delete_user(user_id)
        LOGGER(__name__).info(f"{user_id}-Removed from Database, since deleted account.")
        return 404, 0
    except errors.UserIsBlocked:
        LOGGER(__name__).info(f"{user_id} -Blocked the bot.")
        return 302, 0
    except errors.PeerIdInvalid:
        await usersDB.delete_user(int(user_id))
        LOGGER(__name__).info(f"{user_id} - PeerIdInvalid")
        return 302, 0
    except BaseException as e:
        LOGGER(__name__).error(e)
        return 400, 0
