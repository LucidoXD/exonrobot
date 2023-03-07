from ..database import chatDB
from .cache import Cache
from typing import Any


async def getSettings(groupID: int, chatTitle: str = "", force: bool = False) -> dict:
    if force:
        Cache.SETTINGS_CACHE[groupID] = await chatDB.getConfig(groupID, chatTitle)
    if groupID in Cache.SETTINGS_CACHE:
        return Cache.SETTINGS_CACHE[groupID]
    Cache.SETTINGS_CACHE[groupID] = await chatDB.getConfig(groupID, chatTitle)
    return Cache.SETTINGS_CACHE[groupID]


async def updateSettings(groupID: int, key: str, value: Any, sub: str = None):
    settings = await getSettings(groupID)
    if sub:
        settings[key][sub] = value
    else:
        settings[key] = value
    Cache.SETTINGS_CACHE[groupID] = settings
    await chatDB.col.update_one({"chatID": groupID}, {"$set": settings})
    return settings
