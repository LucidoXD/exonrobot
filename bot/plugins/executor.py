import asyncio
import io
import keyword
import os
import re
import shlex
import sys
import threading
import traceback
from contextlib import contextmanager
from enum import Enum
from getpass import getuser
from typing import Any, Awaitable, Callable, Dict, Iterable, Optional, Tuple

import aiofiles
from bot import Bot, bot
from pyrogram import errors, filters, types
from pyrogram.types import Message
from pyrogram.types.messages_and_media.message import Str

from ..config import Config
from ..utils.tools import runcmd, submit_thread

try:
    from os import geteuid, getpgid, killpg, setsid  # type: ignore
    from signal import SIGKILL
except ImportError:
    from os import kill as killpg
    from signal import CTRL_C_EVENT as SIGKILL  # type: ignore

    def geteuid() -> int:
        return 1

    def getpgid(arg: Any) -> Any:
        return arg
    setsid = None

MSG_IDS_EVAL: Dict[int, asyncio.Future] = {}
_KEY = '_OLD'
_EVAL_TASKS: Dict[asyncio.Future, str] = {}


def input_checker(func: Callable[[Bot, Message], Awaitable[Any]]):
    async def wrapper(bot, message: Message) -> None:
        replied = message.reply_to_message
        cmd = message.text

        if not cmd:
            if (func.__name__ == "eval_"
                    and replied and replied.document
                    and replied.document.file_name.endswith(('.txt', '.py'))
                    and replied.document.file_size <= 2097152):

                dl_loc = await replied.download()
                async with aiofiles.open(dl_loc) as jv:
                    cmd += " " + await jv.read()
                    setattr(message, 'is_file', True)
                os.remove(dl_loc)
            else:
                await message.reply("No Command Found!")
                return

        cmd = message.text
        await func(bot, message)
    return wrapper


async def edit_or_file(text: str, msg: types.Message):
    try:
        await msg.edit(text)
    except errors.MessageTooLong:
        doc = io.BytesIO(text.encode())
        doc.name = 'out.txt'
        await msg.delete()
        await msg.reply_document(doc)




@Bot.on_message(filters.command('exec') & filters.user(Config.SUDO_USERS))  # type: ignore
@input_checker
async def exec_(_: Bot, msg: Message):
    """ run commands in exec """
    message = await msg.reply("`Executing exec ...`")
    try:
        cmd = msg.text.split(None, maxsplit=1)[1]
    except Exception:
        return await message.edit("no command found!")

    try:
        out, err, ret, pid = await runcmd(cmd)
    except Exception as t_e:  # pylint: disable=broad-except
        await edit_or_file(str(t_e), message)
        return

    output = f"**EXEC**:\n\n\
__Command:__\n`{cmd}`\n__PID:__\n`{pid}`\n__RETURN:__\n`{ret}`\n\n\
**stderr:**\n`{err or 'no error'}`\n\n**stdout:**\n``{out or 'no output'}`` "
    await edit_or_file(output, message)


@Bot.on_message(filters.command('eval') & filters.user(Config.SUDO_USERS))  # type: ignore
@input_checker
async def eval_(bot: Bot, message: types.Message):
    """ run python code """
    for t in tuple(_EVAL_TASKS):
        msg_id = _EVAL_TASKS[t]['msg_id']  # type: ignore
        if t.done():
            del MSG_IDS_EVAL[msg_id]  # type: ignore
            del _EVAL_TASKS[t]
    try:
        content = message.text.split(None, maxsplit=1)[1]
    except:
        return await message.reply("no command!")

    
    if content == '-l':
        if _EVAL_TASKS:
            out = "**Eval Tasks**\n\n"
            i = 0
            for c in _EVAL_TASKS.values():
                out += f"**{i}** - `{c['cmd']}`\n"  # type: ignore
                i += 1
            out += f"\nuse `/eval -c [id]` to Cancel"
            await message.reply(out)
        else:
            await message.reply("No running eval tasks !")
        return

    size = len(_EVAL_TASKS)

    if (content == '-c' or content == '-ca') and size == 0:
        await message.reply("No running eval tasks !")
        return

    if content == '-ca':
        for t in _EVAL_TASKS:
            t.cancel()
        await message.reply(f"Canceled all running eval tasks [{size}] !")
        return

    if content.startswith('-c'):
        
        t_id = content.split(None, maxsplit=1)[1]
        try:
            t_id = int(t_id)
        except Exception:
            return await message.reply('Invalid ID')
        if t_id < 0 or t_id >= size:
            await message.reply(f"Invalid eval task id [{t_id}] !")
            return
        tuple(_EVAL_TASKS)[t_id].cancel()
        await message.reply(f"Canceled eval task [{t_id}] !")
        return

    cmd = content
    if not cmd:
        await message.reply("Unable to Parse Input!")
        return

    msg = message
    replied = message.reply_to_message
    if (replied and replied.from_user
            and replied.from_user.is_self and isinstance(replied.text, Str)):
        msg = replied

    sts = await msg.reply("`Executing eval ...`")

    is_file = getattr(message, 'is_file', False)
    try:
        flag, cmd = content.split(None, maxsplit=1)[0]
    except:
        flag, cmd = '', content
    if flag == '-n':
        context_type = _ContextType.NEW

    elif flag == '-p':
        context_type = _ContextType.PRIVATE
    else:
        context_type = _ContextType.GLOBAL

    async def _callback(output: Optional[str], errored: bool):
        final = ""
        final += "**>** " + replied.link if is_file else f'```python\n{cmd}```' + "\n\n"
        if isinstance(output, str):
            output = output.strip()
            if output == '':
                output = None
        if output is not None:
            if errored:
                final += "**ERROR**: \n\n"
            final += f"**>>** ```python\n{output}```"
        if final:
            await edit_or_file(final, sts)
        else:
            await sts.edit('!no return')


    _g, _l = _context(
        context_type, bot=bot, message=message, replied=message.reply_to_message, chat=message.chat)
    l_d = {}
    try:
        exec(_wrap_code(cmd, _l.keys()), _g, l_d)  # nosec pylint: disable=W0122
    except Exception:  # pylint: disable=broad-except
        _g[_KEY] = _l
        await _callback(traceback.format_exc(), True)
        return

    future = asyncio.get_running_loop().create_future()
    submit_thread(_run_coro, future, l_d['__aexec'](*_l.values()), _callback)
    hint = cmd.split('\n')[0]
    _EVAL_TASKS[future] = {'cmd': hint[:25] + "..." if len(hint) > 25 else hint, 'msg_id': sts.id}  # type: ignore
    MSG_IDS_EVAL[sts.id] = future

    try:
        await future
    except asyncio.CancelledError:
        await message.reply(f"**EVAL Process Canceled!**\n\n```python\n{cmd}```")
    finally:
        _EVAL_TASKS.pop(future, None)
        MSG_IDS_EVAL.pop(sts.id)


@Bot.on_message(filters.command('cancel') & filters.user(Config.SUDO_USERS))  # type: ignore
async def cancel_eval_tasks(_: Bot, msg: types.Message):
    if not msg.reply_to_message:
        return await msg.reply('Reply To A Message')
    
    msg_id = msg.reply_to_message_id
    futu = MSG_IDS_EVAL.get(msg_id)
    if not futu:
        return await msg.reply('Nothing to cancel')
    futu.cancel()



@Bot.on_message(filters.command('term') & filters.user(Config.SUDO_USERS))  # type: ignore
@input_checker
async def term_(bot: Bot, message: Message):
    """ run commands in shell (terminal with live update) """
    try:
        cmd = message.text.split(None, maxsplit=1)[1]
    except:
        return await message.reply("NO CMD")
    sts = await message.reply("`Executing terminal ...`")
    
    try:
        parsed_cmd = parse_py_template(cmd, message)
    except Exception as e:  # pylint: disable=broad-except
        await edit_or_file(str(e), sts)
        await edit_or_file(f"**Exception**: {type(e).__name__}\n**Message**: " + str(e), sts)
        return
    try:
        t_obj = await Term.execute(parsed_cmd)  # type: Term
    except Exception as t_e:  # pylint: disable=broad-except
        await edit_or_file(str(t_e), sts)
        return

    cur_user = getuser()
    uid = geteuid()

    prefix = f"<b>{cur_user}:~#</b>" if uid == 0 else f"<b>{cur_user}:~$</b>"
    output = f"{prefix} <pre>{cmd}</pre>\n"

    #with message.cancel_callback(t_obj.cancel):
    await t_obj.init()
    while not t_obj.finished:
        await edit_or_file(f"{output}<pre>{t_obj.line}</pre>", sts)
        await t_obj.wait(10)
    if t_obj.cancelled:
        await message.reply("Cancelled")
        return

    out_data = f"{output}<pre>{t_obj.output}</pre>\n{prefix}"
    await edit_or_file(
        out_data, sts)


def parse_py_template(cmd: str, msg: Message):
    glo, loc = _context(_ContextType.PRIVATE, message=msg, replied=msg.reply_to_message)

    def replacer(mobj):
        return shlex.quote(str(eval(mobj.expand(r"\1"), glo, loc)))  # nosec pylint: disable=W0123
    return re.sub(r"{{(.+?)}}", replacer, cmd)


class _ContextType(Enum):
    GLOBAL = 0
    PRIVATE = 1
    NEW = 2


def _context(context_type: _ContextType, **kwargs) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if context_type == _ContextType.NEW:
        try:
            del globals()[_KEY]
        except KeyError:
            pass
    if _KEY not in globals():
        globals()[_KEY] = globals().copy()
    _g = globals()[_KEY]
    if context_type == _ContextType.PRIVATE:
        _g = _g.copy()
    _l = _g.pop(_KEY, {})
    _l.update(kwargs)
    return _g, _l


def _wrap_code(code: str, args: Iterable[str]) -> str:
    head = "async def __aexec(" + ', '.join(args) + "):\n try:\n  "
    tail = "\n finally: globals()['" + _KEY + "'] = locals()"
    if '\n' in code:
        code = code.replace('\n', '\n  ')
    elif (any(True for k_ in keyword.kwlist if k_ not in (
            'True', 'False', 'None', 'lambda', 'await') and code.startswith(f"{k_} "))
          or ('=' in code and '==' not in code)):
        code = f"\n  {code}"
    else:
        code = f"\n  return {code}"
    return head + code + tail


def _run_coro(future: asyncio.Future, coro: Awaitable[Any],
              callback: Callable[[str, bool], Awaitable[Any]]) -> None:
    loop = asyncio.new_event_loop()
    task = loop.create_task(coro)  # type: ignore
    bot.loop.call_soon_threadsafe(future.add_done_callback,
                                     lambda _: (loop.is_running() and future.cancelled()
                                                and loop.call_soon_threadsafe(task.cancel)))
    try:
        ret, exc = None, None
        with redirect() as out:
            try:
                ret = loop.run_until_complete(task)
            except asyncio.CancelledError:
                return
            except Exception:  # pylint: disable=broad-except
                exc = traceback.format_exc().strip()
            output = exc or out.getvalue()  # type: ignore
            if ret is not None:
                output += str(ret)
        loop.run_until_complete(callback(output, exc is not None))
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        bot.loop.call_soon_threadsafe(lambda: future.done() or future.set_result(None))


_PROXIES = {}


class _Wrapper:
    def __init__(self, original):
        self._original = original

    def __getattr__(self, name: str):
        return getattr(_PROXIES.get(threading.current_thread().ident, self._original), name)


sys.stdout = _Wrapper(sys.stdout)
sys.__stdout__ = _Wrapper(sys.__stdout__)
sys.stderr = _Wrapper(sys.stderr)
sys.__stderr__ = _Wrapper(sys.__stderr__)


@contextmanager
def redirect() -> io.StringIO:  # type: ignore
    ident = threading.current_thread().ident
    source = io.StringIO()
    _PROXIES[ident] = source
    try:
        yield source
    finally:
        del _PROXIES[ident]
        source.close()


class Term:
    """ live update term class """

    def __init__(self, process: asyncio.subprocess.Process) -> None:
        self._process = process
        self._line = b''
        self._output = b''
        self._init = asyncio.Event()
        self._is_init = False
        self._cancelled = False
        self._finished = False
        self._loop = asyncio.get_running_loop()
        self._listener = self._loop.create_future()

    @property
    def line(self) -> str:
        return self._by_to_str(self._line)

    @property
    def output(self) -> str:
        return self._by_to_str(self._output)

    @staticmethod
    def _by_to_str(data: bytes) -> str:
        return data.decode('utf-8', 'replace').strip()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def finished(self) -> bool:
        return self._finished

    async def init(self) -> None:
        await self._init.wait()

    async def wait(self, timeout: int) -> None:
        self._check_listener()
        try:
            await asyncio.wait_for(self._listener, timeout)
        except asyncio.TimeoutError:
            pass

    def _check_listener(self) -> None:
        if self._listener.done():
            self._listener = self._loop.create_future()

    def cancel(self) -> None:
        if self._cancelled or self._finished:
            return
        killpg(getpgid(self._process.pid), SIGKILL)
        self._cancelled = True

    @classmethod
    async def execute(cls, cmd: str) -> 'Term':
        kwargs = dict(stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        if setsid:
            kwargs['preexec_fn'] = setsid  # type: ignore
        process = await asyncio.create_subprocess_shell(cmd, **kwargs)
        t_obj = cls(process)
        t_obj._start()
        return t_obj

    def _start(self) -> None:
        self._loop.create_task(self._worker())

    async def _worker(self) -> None:
        if self._cancelled or self._finished:
            return
        await asyncio.wait([self._read_stdout(), self._read_stderr()])
        await self._process.wait()
        self._finish()

    async def _read_stdout(self) -> None:
        await self._read(self._process.stdout)  # type: ignore

    async def _read_stderr(self) -> None:
        await self._read(self._process.stderr)  # type: ignore

    async def _read(self, reader: asyncio.StreamReader) -> None:
        while True:
            line = await reader.readline()
            if not line:
                break
            self._append(line)

    def _append(self, line: bytes) -> None:
        self._line = line
        self._output += line
        self._check_init()

    def _check_init(self) -> None:
        if self._is_init:
            return
        self._loop.call_later(1, self._init.set)
        self._is_init = True

    def _finish(self) -> None:
        if self._finished:
            return
        self._init.set()
        self._finished = True
        if not self._listener.done():
            self._listener.set_result(None)
