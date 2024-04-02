from datetime import datetime
from libs.mongo_db import MongoDB
from pydantic import BaseModel
from typing import List, Union


class LoginLog(BaseModel):
    account_uuid: str
    result: str
    create_at: datetime

    @classmethod
    def insert(cls, account_uuid: str, result: str):
        loginLog = LoginLog.get_example()
        loginLog.account_uuid = account_uuid
        loginLog.result = result
        data_dict = dict(loginLog)
        MongoDB.insert(collection="login-log", data=data_dict)
        return

    @classmethod
    def find_many(cls, query: dict) -> List:
        result = []
        login_log_dict = MongoDB.find_many(collection="login-log", query=query)
        for login_log in login_log_dict:
            result.append(cls(**login_log))
        return result

    @classmethod
    def find_one(cls, query: dict) -> Union["LoginLog", None]:
        login_log_dict = MongoDB.find_one(collection="login-log", query=query)
        if login_log_dict is None:
            return None
        else:
            return cls(**login_log_dict)

    @classmethod
    def get_example(cls) -> "LoginLog":
        return cls(
            account_uuid="",
            result="",
            create_at=datetime.now(),
        )
