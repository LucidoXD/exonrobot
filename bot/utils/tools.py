import asyncio
import atexit
import base64
import shlex
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from functools import partial, wraps
from typing import Any, Callable, Tuple, List, Union, Dict
from .cache import Cache
from pyrogram import types, enums, filters
from bot import bot

from .logger import LOGGER

EXECUTOR = ThreadPoolExecutor(150)

MAX = EXECUTOR._max_workers


def b64_encode(s: str) -> str:

    return base64.urlsafe_b64encode(s.encode("ascii")).decode().strip("=")


def b64_decode(s: str) -> str:
    return (base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))).decode("ascii")


def generate_secret():
    string = uuid.uuid4().hex.upper()
    return string + str(round(time.time()))


def submit_thread(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Future:
    """submit thread to thread pool"""
    return EXECUTOR.submit(func, *args, **kwargs)


def run_in_thread(func: Callable[..., Any]) -> Callable[..., Any]:
    """run in a thread"""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(EXECUTOR, partial(func, *args, **kwargs))

    return wrapper


def buildKeyBoard(data: List[List[Tuple[str, str]]]):
    return types.InlineKeyboardMarkup(
        [[types.InlineKeyboardButton(i, j) for i, j in l] for l in data]
    )


async def runcmd(cmd: str) -> Tuple[str, str, int, int]:
    """run command in terminal"""
    args = shlex.split(cmd)
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return (
        stdout.decode("utf-8", "replace").strip(),
        stderr.decode("utf-8", "replace").strip(),
        process.returncode,
        process.pid,
    )  # type: ignore


def getButtons(
    data: dict, row: int = 3, close: bool = False, back: bool = False
) -> List[List[types.InlineKeyboardButton]]:
    main = []
    sub = []
    for i in data:
        sub.append(types.InlineKeyboardButton(f"{data[i]}", callback_data=i))
        if len(sub) == row:
            main.append(sub.copy())
            sub.clear()
    if len(sub) > 0:
        main.append(sub.copy())
        sub.clear()
    _closeBack = []
    if back:
        _closeBack.append(types.InlineKeyboardButton("🔙 Back", callback_data="back"))
    if close:
        _closeBack.append(types.InlineKeyboardButton("✖️ Close", callback_data="close"))
    if _closeBack:
        main.append(_closeBack)
    return main


def getYesOrNo(yes: str = "✅ Yes", no: str = "✖️ No"):
    return [
        [
            types.InlineKeyboardButton(yes, callback_data="yes"),
            types.InlineKeyboardButton(no, callback_data="no"),
        ]
    ]


async def getCallBackQuery(
    msg: types.Message, silent: bool = False, adminOnly: bool = False
) -> Union[types.CallbackQuery, None]:
    while bot.is_idling:
        try:
            query = await bot.wait_for_callback_query(msg.chat.id, msg.id, timeout=300)
        except asyncio.TimeoutError:
            if silent:
                await msg.delete()
                return None
            await msg.edit(
                "`Maximum time exceeded`", reply_markup=types.ReplyKeyboardRemove()
            )
            return None
        else:
            if adminOnly:
                _, admins = await getAdmins(msg.chat.id)
                if query.from_user.id not in admins:
                    await query.answer("Unauthorized \n!admin only command")
                    continue
            return query


async def get_input(
    msg: types.Message, timeout: int = 600, silent: bool = False, fromUser: int = None
):
    while bot.is_idling:
        try:
            text = await bot.wait_for_message(
                msg.chat.id, timeout=timeout, filters=filters.incoming
            )
        except asyncio.TimeoutError:
            if silent:
                await msg.delete()
                return ""
            try:
                await msg.reply(
                    "`Maximum time exceeded.`", reply_markup=types.ReplyKeyboardRemove()
                )
            except Exception:
                pass
            return ""
        else:
            if fromUser and not text.from_user:
                continue
            elif fromUser and fromUser != text.from_user.id:
                continue
            if text.text:
                if text.text.lower() == "/cancel":
                    await msg.reply(
                        "`Cancelled`", reply_markup=types.ReplyKeyboardRemove()
                    )
                    return ""
                return text.text
            else:
                await msg.reply("`Send as text message.\nUse /cancel to cancel this.`")
                continue


async def getAdmins(
    group: int, force: bool = False
) -> Tuple[Dict[int, types.ChatMember], List[int]]:
    if group in Cache.ADMINS:
        if time.time() - Cache.ADMINS[group]["time"] > 1200:  # type: ignore
            force = True
        if not force:
            return Cache.ADMINS[group]["admins"], Cache.ADMINS[group]["list"]  # type: ignore

    admins = {}
    _list = []
    async for admin in bot.get_chat_members(
        group, filter=enums.ChatMembersFilter.ADMINISTRATORS
    ):  # type: ignore
        admins[admin.user.id] = admin
        _list.append(admin.user.id)
    Cache.ADMINS[group] = {"admins": admins, "list": _list, "time": time.time()}
    return admins, _list


def _stop():
    EXECUTOR.shutdown()
    LOGGER(__name__).info(f"Stopped Pool : {MAX} Workers")


atexit.register(_stop)
