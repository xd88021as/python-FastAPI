from enum import IntEnum
from libs.mongo_db import MongoDB
from pydantic import BaseModel
from typing import List, Union


class ResourceEnum(IntEnum):
    SelfieAuth = 1
    PsDetect = 2


class Resource(BaseModel):
    id: int
    name: str
    price: float
    currency: str

    @classmethod
    def find_many(cls, query: dict) -> List:
        result = []
        resource_dict = MongoDB.find_many(collection="resource", query=query)
        for resource in resource_dict:
            result.append(cls(**resource))
        return result

    @classmethod
    def find_one(cls, query: dict) -> Union["Resource", None]:
        resource_dict = MongoDB.find_one(collection="resource", query=query)
        if resource_dict is None:
            return None
        else:
            return cls(**resource_dict)

    @classmethod
    def insert_default(cls):
        if Resource.find_one({}) is None:
            resource_list = [
                {"id": ResourceEnum.SelfieAuth, "name": "SelfieAuth 持證自拍驗證",
                    "price": 25.0, "currency": "TWD"},
                {"id": ResourceEnum.PsDetect, "name": "PsDetect P圖偵測",
                    "price": 20.0, "currency": "TWD"}
            ]
            MongoDB.insert_many(collection="resource", data=resource_list)
