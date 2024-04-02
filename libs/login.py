
from fastapi import HTTPException, status
from libs.account import Account
from libs.encryption import Aes
from libs.login_log import LoginLog
from libs.token import Token
from libs.utils import Config
from pydantic import BaseModel

config = Config.get()


class Login(BaseModel):

    class PostBody(BaseModel):
        email: str
        password: str

    class PostResponse(BaseModel):
        token: str

    def get_token(
        data: "Login.PostBody",
    ) -> "Login.PostResponse":
        account = Account.find_one(query={"email": data.email})
        if account:
            password = Aes.encrypt(
                key=config.encryption.aes.key, data=data.password, iv=config.encryption.aes.iv
            )
            if account.password == password:
                payload = {
                    "uuid": account.uuid,
                    "email": account.email,
                    "role_id": account.role_id,
                }
                LoginLog.insert(account_uuid=account.uuid, result="success")
                return {"token": Token.jwt_encode(payload=payload)}

        LoginLog.insert(account_uuid=account.uuid, result="fault")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤"
        )
