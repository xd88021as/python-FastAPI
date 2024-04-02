import datetime
from enum import Enum, IntEnum
import json
from typing import Union
from fastapi import Body
import jwt
from pydantic import root_validator
import requests
import uuid
from pathlib import Path
import rstr

from .utils import Config, BaseModel, logger

# 發證縣市機關簡稱與代碼對照表字典
ISSUE_SITE_ID_AND_STR_MAPPING = {
    "65000": "新北市",  # 新北市必須要放在本對照表第一個位置, 否則輸入文本可能會被誤認為「北市」
    "09007": "連江",
    "09020": "金門",
    "10001": "北縣",
    "10002": "宜縣",
    "10003": "桃縣",
    "10004": "竹縣",
    "10005": "苗縣",
    "10006": "中縣",
    "10007": "彰縣",
    "10008": "投縣",
    "10009": "雲縣",
    "10010": "嘉縣",
    "10011": "南縣",
    "10012": "高縣",
    "10013": "屏縣",
    "10014": "東縣",
    "10015": "花縣",
    "10016": "澎縣",
    "10017": "基市",
    "10018": "竹市",
    "66000": "中市",
    "10020": "嘉市",
    "67000": "南市",
    "63000": "北市",
    "64000": "高市",
    "68000": "桃市",
}

# 領補換類別與代碼對照表字典
APPLY_CODE_INFO_AND_MAPPING = {
    "1": "初發",
    "2": "補發",
    "3": "換發",
}

# 身分證驗證結果代碼與訊息對照字典
CHECKIDCARDAPPLY_CODE_AND_MSG_MAPPING = {
    "1": "國民身分證資料與檔存資料相符",
    "2": "身分證字號目前驗證資料錯誤次數已達 1 次，今日錯誤累積達 3 次後，此身分證字號將無法查詢。",
    "3": "身分證字號目前驗證資料錯誤次數已達 2 次，今日錯誤累積達 3 次後，此身分證字號將無法查詢。",
    "4": "身分證字號目前驗證資料錯誤次數已達 3 次，今日錯誤累積達 3 次後，此身分證字號將無法查詢。(*該次查詢有進行查驗比對但比對結果不相符)",
    "5": "身分證字號驗證資料錯誤次數已達 3 次，今日無法查詢，請明日再查!!(*該次查詢無進行查驗比對)",
    "6": "您所查詢的國民身分證字號已停止使用。",
    "7": "您所查詢的國民身分證，業依當事人申請登錄掛失。",
    "8": "單一使用者出現異常使用情形，暫停使用者權限。"
}

# 內政部連結應用系統回應碼與訊息對照字典
RDCODE_AND_MSG_MAPPING = {
    "RS3811": "連結機關作業管理資料未建, 請重新輸入(請檢查 orgId、apId 是否正確)",
    "RS7007": "網路傳送錯誤",
    "RS7009": "查詢作業完成",
    "RS3822": "查詢條件值,不符規定",
}


class _IssueSiteIdEnum(str, Enum):
    """ 發證縣市機關簡稱與代碼枚舉類
    """
    pass


IssueSiteIdEnum = _IssueSiteIdEnum(
    "IssueSiteIdEnum",
    {
        v: k
        for k, v in sorted(
            ISSUE_SITE_ID_AND_STR_MAPPING.items(),
        )
    }
)


class _ApplyCodeIntEnum(IntEnum):
    """ 領補換類別與代碼枚舉類
    """
    pass


ApplyCodeIntEnum = _ApplyCodeIntEnum(
    "ApplyCodeIntEnum",
    {v: k for k, v in APPLY_CODE_INFO_AND_MAPPING.items()}
)


class _RdCodeEnum(str, Enum):
    """ 內政部連結應用系統回應碼枚舉類
    """
    pass


RdCodeEnum = _RdCodeEnum(
    "RdCodeEnum",
    {v: k for k, v in RDCODE_AND_MSG_MAPPING.items()}
)


class _CheckIdCardApplyCodeEnum(IntEnum):
    """ 身分證驗證結果代碼枚舉類
    """
    pass


CheckIdCardApplyCodeEnum = _CheckIdCardApplyCodeEnum(
    "CheckIdCardApplyCodeEnum",
    {v: k for k, v in CHECKIDCARDAPPLY_CODE_AND_MSG_MAPPING.items()}
)

# 戶政司申請資料
ORG_ID = Config.get().household_registration_api.org_id
AP_ID = Config.get().household_registration_api.ap_id
ISS = Config.get().household_registration_api.iss
PRIVATE_KEY = Path("./household_registration_api_private.pem").read_bytes()
# Apache 相關
APACHE_IP = Config.get().household_registration_api.apache_ip
APACHE_PORT = Config.get().household_registration_api.apache_port


class HouseholdRegistrationAPI:
    """ 中華民國內政部戶政司 API

    Ref:
        API 文件: https://drive.google.com/file/d/1QMuN23Svnbxm65wh3Zt4cTrWRUVf-qvo/view?usp=sharing

    """

    class Response(BaseModel):
        """ 回傳資料基礎類別
        """
        class ResponseData(BaseModel):
            checkIdCardApply: CheckIdCardApplyCodeEnum

            class Config:
                fields = {
                    "checkIdCardApply": {
                        "description": (
                            "身分證驗證結果代碼:\n\n" + "\n\n".join([
                                f"{k}: {v}"
                                for k, v in CHECKIDCARDAPPLY_CODE_AND_MSG_MAPPING.items()
                            ])
                        )
                    }
                }

        httpCode: str
        httpMessage: str
        rdCode: Union[RdCodeEnum, str]
        rdMessage: str
        responseData: Union[ResponseData, dict]

        class Config:
            fields = {
                "httpCode": {"description": "HTTP 狀態碼"},
                "httpMessage": {"description": "HTTP 狀態訊息"},
                "rdCode": {
                    "description": "內政部連結應用系統回應碼:\n\n" + "\n\n".join([
                        f"{k}: {v}"
                        for k, v in RDCODE_AND_MSG_MAPPING.items()
                    ])
                },
                "rdMessage": {"description": "內政部連結應用系統回應訊息"},
                "responseData": {"description": "身分證驗證結果"}
            }

    @classmethod
    def update_forward_refs(cls):
        cls.Response.update_forward_refs()
        cls.Response.ResponseData.update_forward_refs()

    class Request(BaseModel):
        person_id: str
        apply_yyy: int
        apply_mm: int
        apply_dd: int
        apply_code_int: int
        issue_site_id: str

        @root_validator
        def idCardStrict_validator(cls, values: dict) -> dict:
            """ 借助 IDCardStrict 的驗證方法
            """
            from libs.id_card import IDCardStrict
            idCardStrict = IDCardStrict(
                **values,
                name="_",
                birth_yyy=1,
                birth_mm=1,
                birth_dd=1,
            )
            return {
                **values,
                # 回傳時，更新身分證字號 (小寫會變成大寫)
                "person_id": idCardStrict.person_id,
            }

        class Config:
            fields = {
                "person_id": {"description": "身分證號碼"},
                "apply_yyy": {"description": "發證日期(民國年)"},
                "apply_mm": {"description": "發證日期(月)"},
                "apply_dd": {"description": "發證日期(日)"},
                "apply_code_int": {
                    "description": "領補換類別代碼 (" + " / ".join([
                        f"{v}: {k}"
                        for k, v in ApplyCodeIntEnum.__members__.items()
                    ]) + ")"
                },
                "issue_site_id": {
                    "description": "發卡機關代碼 (" + " / ".join([
                        f"{v}: {k}"
                        for k, v in IssueSiteIdEnum.__members__.items()
                    ]) + ")"
                },
            }

        @classmethod
        def get_example_body(cls) -> Body:
            """ 獲取請求範例
            """
            return Body(
                ...,
                examples={
                    "Peter": dict(
                        value=cls(
                            person_id="F128490777",
                            apply_yyy=103,
                            apply_mm=12,
                            apply_dd=26,
                            apply_code_int=(
                                ApplyCodeIntEnum.__members__["補發"].value
                            ),
                            issue_site_id=(
                                IssueSiteIdEnum.__members__["新北市"].value
                            ),
                        )
                    )
                }
            )

        def send(self) -> "HouseholdRegistrationAPI.Response":
            """ 辨識身分證是否正確

            Raises:
                HttpError: 網路連線等其他錯誤

            Returns:
                HouseholdRegistrationAPI.Response: 回傳資料

            """
            # 建立請求資料 payload
            now_dt_ts = datetime.datetime.now()
            now_dt_ts_int = int(now_dt_ts.timestamp())
            id_card_info_dict = dict(
                personId=self.person_id,
                applyCode=str(self.apply_code_int),
                applyYyymmdd=f"{self.apply_yyy:03}{self.apply_mm:02}{self.apply_dd:02}",
                issueSiteId=self.issue_site_id
            )
            logger.debug(f"id_card_info_dict: {id_card_info_dict}")
            payload = {
                "orgId": ORG_ID,
                "apId": AP_ID,
                # 普匯金融公司內部員工使用者辨識 ID (使用亂數避免同一個使用者試錯太多而被封鎖)
                "userId": rstr.xeger(r"petertest[A-Z]{3}"),
                "iss": ISS,
                "sub": "綠色便民專案",
                "aud": f"{now_dt_ts:%Y/%m/%d %H:%M:%S}",  # YYYY/MM/DD HH:MM:SS
                "jobId": "V2C201",
                "opType": "RW",
                "iat": now_dt_ts_int - 180,
                "exp": now_dt_ts_int + 180,
                "jti": uuid.uuid4().hex,
                "conditionMap": json.dumps(id_card_info_dict)
            }
            # 加密 payload 產生 JWT
            jwt_encoded_str = jwt.encode(
                payload, PRIVATE_KEY, algorithm="RS256"
            )
            # 送出請求資料
            res = requests.post(
                url=f"http://{APACHE_IP}:{APACHE_PORT}/service-adapter/api/v1.0/id-card/send-request",
                json=dict(
                    headers=json.dumps({
                        "Authorization": f"Bearer {jwt_encoded_str}",
                        "sris-consumerAdminId": "00000000",
                        "Content-Type": "application/json"
                    }),
                )
            )
            # 分析回傳資料並處理錯誤訊息
            res.raise_for_status()
            # print("res.json()", res.json())
            response = HouseholdRegistrationAPI.Response(**res.json())
            return response

            # return None
HouseholdRegistrationAPI.update_forward_refs()
