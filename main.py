from fastapi import (
    BackgroundTasks,
    Body,
    Depends,
    FastAPI,
    HTTPException,
    Path as FastapiPath,
    Query,
    Request,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from libs import (
    health_card,
    id_card,
    id_card_back,
    ps_detect,
)
from libs.account import Account
from libs.credit import Credit
from libs.login import Login
from libs.mongo_db import MongoDB
from libs.resource import Resource
from libs.role import Role
from libs.selfie_verification import SelfieVerificationOut
from libs.task import Task, TaskGetOut, TaskOut
from libs.token import Token
from libs.utils import (
    Image,
    StrictnessIntEnum,
    get_enum_description,
    get_example_200_responses_dict,
    get_example_201_responses_dict,
)
from loguru import logger
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Union, Annotated


import sys
sys.path.append("./frontend")
import frontend  # noqa: E402

# 設定響應錯誤訊息說明
responses = {
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
        "description": "圖片檔案太大."
    }
}

# 建立 app 實例
app = FastAPI(
    title="test AI Kit",
    version="VERSION 2023.10.13.2",
    swagger_ui_parameters={
        # 在 API 文件上展開所有 schema 內容
        "defaultModelExpandDepth": 100,
    },
)

# 建立 OAuth2PasswordBearer 實例
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# 解決 CORS 問題
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def startup_event():
    """ 啟動時執行
    """
    # 設定 APP 全域函數: monogoDB collection: task
    logger.info("Connecting to mongodb...")
    app.mongo_db = MongoDB.get_collection()
    Resource.insert_default()
    Role.insert_default()

    logger.info("API docs 請造訪: http://127.0.0.1:8000/docs")


class ImgPost(BaseModel):
    """ 圖片 POST
    """
    img_base64_str: str = Field(
        None,
        description=(
            "圖片 Base64 值\n\n"
            "圖片格式：JPEG, JPG, PNG\n\n"
            "圖片大小：不大於5M\n\n"
            "`img_base64_str`, `img_url` 二擇一提供，如均提供，則只取imageBase64欄位值\n"
        ),
    )
    img_url: str = Field(
        None,
        description=(
            "圖片網址\n\n"
            "圖片格式：JPEG, JPG, PNG\n\n"
            "圖片大小：不大於5M\n\n"
            "`img_base64_str`, `img_url` 二擇一提供，如均提供，則只取imageBase64欄位值\n"
        ),
    )


@app.post(
    "/account",
    summary="註冊會員",
    response_model=dict,
    responses=responses,
    tags=["會員"],
)
def post_account(
    body: Account.PostBody
):
    if Account.find_one(query={"email": body.email}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="該信箱已註冊過"
        )
    Account.insert(data=body)
    return {"message": f"email:{body.email} 註冊成功"}


@app.get(
    "/account",
    summary="取得會員資料",
    response_model=Union[Account, None],
    responses=responses,
    tags=["會員"],
)
def get_account(
    token: Annotated[str, Depends(oauth2_scheme)],
    uuid: str = Query(None, description="account uuid"),
    email: str = Query(None, description="account email"),
):
    jwtPayload = Token.jwt_decode(token=token)
    Token.verify_token_uuid(payload=jwtPayload, uuid=uuid)
    if uuid:
        return Account.find_one(query={"uuid": uuid})
    elif email:
        return Account.find_one(query={"email": email})
    else:
        return None


@app.patch(
    "/account/{uuid}",
    summary="會員資料更新",
    response_model=dict,
    responses=responses,
    tags=["會員"],
)
def patch_account(
    token: Annotated[str, Depends(oauth2_scheme)],
    uuid: str = FastapiPath(..., description="account uuid"),
    body: Account.PatchBody = Body(...),
):
    jwtPayload = Token.jwt_decode(token=token)
    Token.verify_token_uuid(payload=jwtPayload, uuid=uuid)
    if Account.find_one(query={"uuid": uuid}) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="查無此會員"
        )
    Account.update(uuid=uuid, data=body)
    return {"message": "會員資料更新成功"}


@app.post(
    "/login",
    summary="登入",
    response_model=Login.PostResponse,
    responses=responses,
    tags=["憑證"],
)
def post_login(
    body: Login.PostBody
):
    return Login.get_token(data=body)


@app.post(
    "/token",
    summary="取得Access Token",
    response_model=str,
    responses=responses,
    tags=["憑證"],
)
def post_token(body: Token.PostBody):
    credit = Credit.find_one(query={"api_key": body.api_key})
    if credit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="api_key輸入錯誤"
        )
    account = Account.find_one(query={"uuid": credit.account_uuid})
    payload = {"uuid": account.uuid,
               "email": account.email, "role_id": account.role_id}
    return Token.jwt_encode(payload=payload)


@app.post(
    "/credit",
    summary="新增服務",
    response_model=dict,
    responses=responses,
    tags=["服務"],
)
def post_credit(
    token: Annotated[str, Depends(oauth2_scheme)],
    body: Credit.PostBody,
):
    jwtPayload = Token.jwt_decode(token=token)
    Token.verify_token_uuid(payload=jwtPayload, uuid=body.account_uuid)
    account = Account.find_one(query={"uuid": body.account_uuid})
    resource = Resource.find_one(query={"id": body.resource_id})
    if resource is None or account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="account uuid 或resource id 輸入錯誤"
        )
    if Credit.find_one(query={"account_uuid": body.account_uuid, "resource_id": body.resource_id}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="此帳號已擁有該服務"
        )
    Credit.insert(account_uuid=body.account_uuid, resource_id=body.resource_id)
    return {"message": "服務新增成功"}


@app.get(
    "/credit",
    summary="取得服務資料",
    response_model=Union[Credit, None],
    responses=responses,
    tags=["服務"],
)
def get_credit(
    api_key: str = Query(..., description="credit api_key"),
):
    return Credit.find_one(query={"api_key": api_key})


@app.patch(
    "/credit/{api_key}",
    summary="更新服務資料",
    response_model=dict,
    responses=responses,
    tags=["服務"],
)
def patch_credit(
    token: Annotated[str, Depends(oauth2_scheme)],
    api_key: str = FastapiPath(..., description="credit api_key"),
    body: Credit.PatchBody = Body(...),
):
    jwtPayload = Token.jwt_decode(token=token)
    Token.verify_token_role(payload=jwtPayload, role_name="god")
    credit = Credit.find_one(query={"api_key": api_key})
    if credit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="credit api_key 輸入錯誤"
        )
    Credit.update(api_key=api_key, data=body)
    return {"message": "服務更新成功"}


@app.get(
    "/credit/list",
    summary="取得帳號擁有的服務清單",
    response_model=List,
    responses=responses,
    tags=["服務"],
)
def get_credit_list(
    token: Annotated[str, Depends(oauth2_scheme)],
    account_uuid: str = Query(..., description="account uuid"),
):
    jwtPayload = Token.jwt_decode(token=token)
    Token.verify_token_uuid(payload=jwtPayload, uuid=account_uuid)
    credits = Credit.find_many(query={"account_uuid": account_uuid})
    return credits


@app.post(
    "/v1/selfie-with-taiwanese-id/verify",
    summary="取得身分證正面、身分證反面、健保卡正面、持證自拍照，進行MFA資訊與生物特徽比對之驗證結果",
    status_code=201,
    response_model=TaskOut,
    responses=responses,
    tags=["持證自拍照"],
)
def post_selfie_with_taiwanese_id_verify(
    request: Request,
    background_tasks: BackgroundTasks,
    id_card_img_post: ImgPost = Body(..., description="身分證正面影像"),
    id_card_back_img_post: ImgPost = Body(..., description="身分證反面影像"),
    health_card_img_post: ImgPost = Body(..., description="健保卡影像"),
    hold_card_selfie_img_post: ImgPost = Body(..., description="持證自拍照影像"),
    strictness_int: StrictnessIntEnum = Query(
        StrictnessIntEnum.MEDIUM,
        description=get_enum_description(StrictnessIntEnum),
    )
):
    def get_selfie_verification_out(id_card_image_bytes: bytes,
                                    id_card_back_image_bytes: bytes,
                                    health_card_image_bytes: bytes,
                                    hold_card_selfie_image_bytes: bytes,
                                    strictness_int: int) -> SelfieVerificationOut:
        return SelfieVerificationOut.from_image_bytes(
            id_card_image_bytes=id_card_image_bytes,
            id_card_back_image_bytes=id_card_back_image_bytes,
            health_card_image_bytes=health_card_image_bytes,
            hold_card_selfie_image_bytes=hold_card_selfie_image_bytes,
            strictness_int=strictness_int,
        )

    def get_img_post_bytes(img_post: ImgPost, name: str):
        if img_post.img_base64_str is not None:
            try:
                return Image(base64str=img_post.img_base64_str).get_bytes()
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"無法用此base64識別{name}影像"
                )
        elif img_post.img_url is not None:
            try:
                return Image(url=img_post.img_url).get_bytes()
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"無法用此url識別{name}影像"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{name}影像請傳入base64或url"
            )

    id_card_image_bytes = get_img_post_bytes(id_card_img_post, "身分證正面")
    id_card_back_image_bytes = get_img_post_bytes(
        id_card_back_img_post, "身分證反面")
    health_card_image_bytes = get_img_post_bytes(health_card_img_post, "健保卡")
    hold_card_selfie_image_bytes = get_img_post_bytes(
        hold_card_selfie_img_post,
        "持證自拍照")

    task = Task.from_request(request=request)
    background_tasks.add_task(
        task.run,
        func_=get_selfie_verification_out,
        func_kwargs={"id_card_image_bytes": id_card_image_bytes,
                     "id_card_back_image_bytes": id_card_back_image_bytes,
                     "health_card_image_bytes": health_card_image_bytes,
                     "hold_card_selfie_image_bytes": hold_card_selfie_image_bytes,
                     "strictness_int": strictness_int},
    )
    return TaskOut(task_id=task.task_id)


@app.get(
    "/v1/selfie-with-taiwanese-id/verify",
    summary="取得身分證正面、身分證反面、健保卡正面、持證自拍照，進行MFA資訊與生物特徽比對之驗證結果",
    response_model=Union[SelfieVerificationOut, str],
    responses=responses,
    tags=["持證自拍照"],
)
def get_selfie_with_taiwanese_id_verify(
    task_id: str = Query(
        ...,
        description="任務 ID",
    ),
):
    taskGetOut = TaskGetOut.get(task_id=task_id)
    if taskGetOut is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"找不到 task_id: {task_id}",
        )
    if taskGetOut.response_body is not None:
        return taskGetOut.response_body
    else:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="MFA資訊與生物特徵比對進行中",
        )

frontend.init(app)
