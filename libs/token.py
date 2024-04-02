
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from libs.role import Role
from libs.utils import Config
from pydantic import BaseModel
from typing import Union
import jwt

config = Config.get()


class Token(BaseModel):

    class PostBody(BaseModel):
        api_key: str

    class Payload(BaseModel):
        uuid: str
        email: str
        role_id: int

    class JwtPayload(BaseModel):
        uuid: str
        email: str
        role_id: int
        exp: datetime

    def jwt_encode(
        payload: "Token.Payload",
    ) -> str:
        return jwt.encode(
            payload={"exp": datetime.utcnow() + timedelta(minutes=15),
                     **payload},
            key=config.jwt.key
        )

    def jwt_decode(
        token: str,
    ) -> Union["Token.JwtPayload", str]:
        try:
            return jwt.decode(token, config.jwt.key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="JWT 已过期"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="JWT 無效"
            )
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"其他異常，請聯絡客服。 err_msg:{err}"
            )

    def verify_token_uuid(
        payload: "Token.Payload",
        uuid: str,
    ):
        if uuid is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="驗證Jwt uuid時請帶入account uuid"
            )
        # Token的role為god時直接通過驗證
        role = Role.find_one(query={"id": payload["role_id"]})
        if role.name == "god":
            return
        if payload["uuid"] != uuid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="此Jwt 無權限操作此動作"
            )

    def verify_token_role(
        payload: "Token.Payload",
        role_name: str,
    ):
        if role_name is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="驗證Jwt role時請帶入role name"
            )
        # Token的role為god時直接通過驗證
        role = Role.find_one(query={"id": payload["role_id"]})
        if role.name == "god":
            return
        if role.name != role_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="此Jwt 無權限操作此動作"
            )
