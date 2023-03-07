from typing import Dict, Union, List
from pyrogram.types import ChatMember


class Cache:
    BANNED: List[int] = []
    CANCEL_BROADCAST: bool = False
    ADMINS: Dict[int, Dict[str, Union[List[int], float, Dict[int, ChatMember]]]] = {}
    SETTINGS_CACHE = {}
    FORBIDDEN = {}
