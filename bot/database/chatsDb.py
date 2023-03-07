from .mongoDb import MongoDb


class ChatsDB(MongoDb):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection("chats")

    def newChat(self, chatID: int, title: str = ""):
        return dict(
            chatID=chatID,
            name=title,
            autoDelete=dict(status=False, delay=10, var="all"),
            autoAccept=dict(
                status=True,
                delay=0,
                var=dict(
                    type="text",
                    text="Hey {first}, Your request to join {chatname} will be approved soon!",
                    file_id=None,
                ),
            ),
            welcome_settings=dict(
                clean=False,
                message=dict(
                    type="text",
                    text="Hey {first}, welcome to {chatname}!",
                    file_id=None,
                ),
                last=None,
                status=True,
            ),
            goodbye_settings=dict(
                clean=False,
                message=dict(
                    type="text",
                    text="Sad to see you leaving {first}.\nTake Care!",
                    file_id=None,
                ),
                last=None,
                status=True,
            ),
        )

    async def getConfig(self, chatID, title: str = ""):
        config = await self.col.find_one({"chatID": chatID})  # type: ignore # type: ignore
        if not config:
            await self.col.insert_one(self.newChat(chatID, title))  # type: ignore
            return self.newChat(chatID, title)
        return config


chatDB = ChatsDB()
