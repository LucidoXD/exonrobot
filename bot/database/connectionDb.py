from .mongoDb import MongoDb


class ConnectionDB(MongoDb):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection("connections")

    def newConnection(self, userID):
        return dict(userID=userID, chats=dict(group=[], supergroup=[], channel=[]))


conDB = ConnectionDB()
