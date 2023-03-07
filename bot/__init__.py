from .config import Config

from .client import Client
from .utils.initialization import check_pending
from .utils.logger import LOGGER


class Bot(Client):
    def __init__(self, name: str):
        self.name = name
        self.is_idling: bool = False
        super().__init__(self.name)

    async def start(self):
        await super().start()
        await self.send_message(Config.LOG_CHANNEL, f"#START\nBot [`@{self.me.username}`] started")
        self.loop.create_task(check_pending(self))
        LOGGER(__name__).info("--- Bot Initialized--- ")

    async def stop(self, *args):
        await self.send_message(Config.LOG_CHANNEL, f"#STOP\nBot [`@{self.me.username}`] Stopped")
        await super().stop()


bot = Bot(Config.BOT_NAME)
