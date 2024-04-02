import binascii
import datetime
import PIL.Image
import requests
import uuid
from fastapi import HTTPException, Request, status
from libs.mongo_db import MongoDB
from pydantic import BaseModel, Field
from typing import Callable, Optional, Union
from typing_extensions import Literal


class TaskBase(BaseModel):
    """ 請求任務基底類
    """
    task_id: str

    class Config:
        fields = {
            "task_id": {"description": "任務 id"},
            "request_dt": {"description": "請求時間"},
            "method": {"description": "請求方法"},
            "path": {"description": "請求路徑"},
            "headers": {"description": "請求標頭"},
            "response_dt": {"description": "回應時間"},
            "response_status": {"description": "回應狀態"},
            "response_headers": {"description": "回應標頭"},
            "response_body": {"description": "回應內容"},

        }


class TaskOut(BaseModel):
    task_id: str = Field(
        ...,
        description="任務 ID",
    )

    @classmethod
    def get_example(cls) -> "TaskOut":
        return cls(
            task_id=uuid.uuid4().hex,
        )


class TaskGetOut(TaskBase):
    """ GET 請求任務結果響應
    """
    request_dt: datetime.datetime
    method: Literal["POST", "GET"]
    path: str
    headers: dict

    response_dt: datetime.datetime = None
    response_status: int = None
    response_body: Union[list, dict] = None
    response_message: str = None

    @classmethod
    def get(cls, task_id: str) -> Optional["TaskGetOut"]:
        """ 取得請求任務

        Args:
            task_id (str): 請求任務 id

        Returns:
            Optional["TaskGetOut"]: 請求任務
        """

        task_dict = MongoDB.find_one(
            collection="task", query={"task_id": task_id})

        if task_dict is None:
            return None
        return cls(**task_dict)


class Task(TaskGetOut):
    """ 任務
    """

    @classmethod
    def from_request(cls, request: Request) -> "Task":
        """ 從 request 建立任務

        Args:
            request (Request): 請求

        Returns:
            Task: 任務
        """
        task = cls(
            task_id=str(uuid.uuid4().hex),
            request_dt=datetime.datetime.now(),
            method=request.method,
            path=request.url.path,
            headers=request.headers,
        )
        return task

    def run(self, func_: Callable, func_kwargs: dict = dict()):
        """ 建立請求任務，並將響應結果儲存於 MongoDB 中 (此過程應於背景執行)
        """

        # 新增請求任務於 MongoDB
        MongoDB.insert(collection="task", data=self.dict())

        # 建立 client 物件，送出請求，並獲得回傳結果
        status_code = status.HTTP_200_OK
        message = None
        res = None
        try:
            res = func_(**func_kwargs)
        except requests.exceptions.ConnectionError as exc:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            message = f"服務未回應. detail: {exc!r}"
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code
            message = f"服務網路連線錯誤. detail: {exc!r}"
        except PIL.Image.DecompressionBombError as exc:
            status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            message = f"圖片壓縮失敗，請檢查圖片大小，若為超大圖片，請將圖片壓縮至 3000 x 3000 像素以下. 原因：{exc!r}"
        except binascii.Error as exc:
            status_code = status.HTTP_400_BAD_REQUEST
            message = f"RSA 解密失敗. detail: {exc!r}"
        except UnicodeDecodeError as exc:
            status_code = status.HTTP_400_BAD_REQUEST
            message = f"AES 解密失敗. detail: {exc!r}"
        except HTTPException as exc:
            status_code = exc.status_code
            message = exc.detail
        except Exception as exc:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            message = f"未知錯誤. detail: {exc!r}"

        response_body = None
        if res is not None:
            if isinstance(res, list):
                response_body = [r.dict() for r in res]
            else:
                response_body = res.dict()

        # 更新請求任務於 MongoDB
        data = {
            "$set": {
                "response_dt": datetime.datetime.utcnow(),
                "response_status": status_code,
                "response_body": response_body,
                "response_message": message,
            }
        }
        MongoDB.update(collection="task",
                       query={"task_id": self.task_id},
                       data=data)
