from enum import IntEnum
from libs.mongo_db import MongoDB
from pydantic import BaseModel
from typing import List, Union


class RoleEnum(IntEnum):
    god = 1
    account = 2


class Role(BaseModel):
    id: int
    name: str

    @classmethod
    def find_many(cls, query: dict) -> List:
        result = []
        role_dict = MongoDB.find_many(collection="role", query=query)
        for role in role_dict:
            result.append(cls(**role))
        return result

    @classmethod
    def find_one(cls, query: dict) -> Union["Role", None]:
        role_dict = MongoDB.find_one(collection="role", query=query)
        if role_dict is None:
            return None
        else:
            return cls(**role_dict)

    @classmethod
    def insert_default(cls):
        if Role.find_one({}) is None:
            role_list = [
                {"id": RoleEnum.god, "name": "god"},
                {"id": RoleEnum.account, "name": "account"}
            ]
            MongoDB.insert_many(collection="role", data=role_list)
