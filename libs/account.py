from libs.encryption import Aes
from libs.mongo_db import MongoDB
from libs.role import RoleEnum
from libs.utils import Config
from pydantic import BaseModel
from typing import Union
import uuid


config = Config.get()


class Account(BaseModel):

    uuid: str
    email: str
    password: str
    name: str
    phone: str
    role_id: int

    class PatchBody(BaseModel):
        name: str
        phone: str

    class PostBody(BaseModel):
        email: str
        password: str

    @classmethod
    def insert(cls, data: "Account.PostBody"):
        account = Account.get_example()
        account.email = data.email
        account.password = Aes.encrypt(
            key=config.encryption.aes.key, data=data.password, iv=config.encryption.aes.iv
        )
        data_dict = dict(account)
        MongoDB.insert(collection="account", data=data_dict)
        MongoDB.create_index(collection="account", key="email")

    @classmethod
    def find_one(cls, query: dict) -> Union["Account", None]:
        account_dict = MongoDB.find_one(collection="account", query=query)
        if account_dict is None:
            return None
        else:
            return cls(**account_dict)

    @classmethod
    def update(cls, uuid: str, data: "Account.PatchBody"):
        query = {
            "uuid": uuid
        }
        data_dict = {
            "$set": dict(data)
        }
        MongoDB.update(collection="account", query=query, data=data_dict)

    @classmethod
    def get_example(cls) -> "Account":
        return cls(
            uuid=str(uuid.uuid4().hex),
            email="",
            password="",
            name="",
            phone="",
            role_id=RoleEnum.account,
        )
