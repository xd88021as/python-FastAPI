from datetime import datetime, timedelta
from libs.mongo_db import MongoDB
from pydantic import BaseModel
from typing import List, Union
import uuid


class Credit(BaseModel):
    api_key: str
    amount: int
    expiration_date: datetime
    account_uuid: str
    resource_id: int

    class PostBody(BaseModel):
        account_uuid: str
        resource_id: int

    class PatchBody(BaseModel):
        amount: int

    @classmethod
    def insert(cls, account_uuid: str, resource_id: int):
        credit = Credit.get_example()
        credit.account_uuid = account_uuid
        credit.resource_id = resource_id
        data_dict = dict(credit)
        MongoDB.insert(collection="credit", data=data_dict)
        MongoDB.create_index(collection="credit", key="api_key")
        return

    @classmethod
    def find_many(cls, query: dict) -> List:
        result = []
        credit_dict = MongoDB.find_many(collection="credit", query=query)
        for credit in credit_dict:
            result.append(cls(**credit))
        return result

    @classmethod
    def find_one(cls, query: dict) -> Union["Credit", None]:
        credit_dict = MongoDB.find_one(collection="credit", query=query)
        if credit_dict is None:
            return None
        else:
            return cls(**credit_dict)

    @classmethod
    def update(cls, api_key: str, data: "Credit.PatchBody"):
        query = {
            "api_key": api_key
        }
        data_dict = {
            "$set": dict(data)
        }
        MongoDB.update(collection="credit", query=query, data=data_dict)

    @classmethod
    def get_example(cls) -> "Credit":
        return cls(
            api_key=str(uuid.uuid4().hex),
            amount=0,
            expiration_date=datetime.utcnow() + timedelta(days=365),
            account_uuid="",
            resource_id=0,
        )
