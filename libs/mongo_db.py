from libs.utils import Config
from loguru import logger
from pydantic import BaseModel
from pymongo import MongoClient, ASCENDING


class MongoDB(BaseModel):

    def get_collection():
        config = Config.get()
        host: str = config.mongo_db.host or "localhost"
        port: int = config.mongo_db.port or 27017
        username: str | None = config.mongo_db.username
        password: str | None = config.mongo_db.password
        database: str | None = config.mongo_db.database
        serverSelectionTimeoutMS: int = 5000
        logger.info(
            f"連線至 MongoDB {host=}, {port=}, {database=}... :")
        if username and password:
            client = MongoClient(
                host=host,
                port=port,
                username=username,
                password=password,
                serverSelectionTimeoutMS=serverSelectionTimeoutMS,
            )
        else:
            client = MongoClient(
                host=host,
                port=port,
                serverSelectionTimeoutMS=serverSelectionTimeoutMS,
            )
        client.server_info()

        return client[database]

    def aggregate(collection: str, list: list):
        from main import app
        return app.mongo_db[collection].aggregate(list)

    def insert(collection: str, data: dict):
        from main import app
        # 新增請求任務於 MongoDB
        return app.mongo_db[collection].insert_one(data)

    def insert_many(collection: str, data: list):
        from main import app
        return app.mongo_db[collection].insert_many(data)

    def find_many(collection: str, query: dict):
        from main import app
        return app.mongo_db[collection].find(query)

    def find_one(collection: str, query: dict):
        from main import app
        return app.mongo_db[collection].find_one(query)

    def update(collection: str, query: dict, data: dict):
        from main import app
        return app.mongo_db[collection].update_one(query, data)

    def create_index(collection: str, key: str):
        from main import app
        app.mongo_db[collection].create_index(
            [(key, ASCENDING)], unique=True)
