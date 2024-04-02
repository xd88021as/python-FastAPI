import datetime
import json
import sys
from enum import IntEnum
from pathlib import Path

from loguru import logger
from pydantic import BaseModel
from tortoise import Tortoise, fields, run_async
from tortoise.models import Model

sys.path.append(str(Path(__file__).parent.parent.parent))  # noqa
from libs.selfie_verification import SelfieVerificationOut
from libs.utils import Image

# 設置 logger
format = (
    # 時間戳 (含時區)
    "<green>{time:YYYY-MM-DD HH:mm:ssZZ}</green>"
    # 等級
    " | <level>{level: <8}</level>"
    # 檔案名稱:函數名稱:行數
    " | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>"
    # 訊息
    " - <level>{message}</level>"
)
log_path = Path(__file__).parent / "logs" / "log.log"
# 修正 log 時間戳: 追加時區
logger.remove()  # 移除原有的設定
logger.add(
    log_path,
    rotation='1 day',
    retention="10 days",
    enqueue=True,
    backtrace=False,
    diagnose=False,
    encoding='utf-8',
    format=format,
)
logger.add(
    sys.stdout,
    format=format,
)


async def init():
    await Tortoise.init(
        config=dict(
            connections=CONFIG.mysql.connections,
            apps={
                "models": {
                    "models": ["__main__"],
                    "default_connection": "default",
                }
            },
            timezone='Asia/Taipei',
        ),
    )


class Mysql(BaseModel):
    username: str
    password: str
    host: str
    port: str

    @property
    def connections(self):
        return {
            "default": {
                "engine": "tortoise.backends.mysql",
                "credentials": {
                    "user": self.username,
                    "password": self.password,
                    "host": self.host,
                    "port": self.port,
                    "database": None,
                }
            }
        }


class Config(BaseModel):
    """ 設定
    """
    mysql: Mysql = None


class P2pUserUserCertificationModel(Model):
    """ 徵信項
    """
    class StatusIntEnum(IntEnum):
        PENDING_TO_VALIDATE = 0  # 待驗證
        SUCCEED = 1  # 驗證成功
        FAILED = 2  # 驗證失敗
        PENDING_TO_REVIEW = 3  # 待人工審核
        NOT_COMPLETED = 4  # 資料尚未填寫完成
        PENDING_TO_AUTHENTICATION = 5  # 等待進行資料真實性驗證
        AUTHENTICATED = 6  # 已驗證資料真實性待使用者送出審核 -> 送出審核後會變為待驗證

    class SubStatusIntEnum(IntEnum):
        NONE = 0  # 無
        WRONG_FORMAT = 1  # 資料格式有誤
        VERIFY_FAILED = 2  # 資料核實失敗
        REVIEW_FAILED = 3  # 未符合授信標準
        NOT_ONE_MONTH = 4  # 資料非近一個月申請

    class CertificateStatusIntEnum(IntEnum):
        NONE = 0  # 無
        SENT_FOR_REVIEW = 1  # 已送出審核

    id = fields.IntField(pk=True)
    user_id = fields.IntField()
    investor = fields.IntField()
    certification_id = fields.IntField()
    content = fields.TextField()
    remark = fields.TextField()
    status = fields.IntEnumField(
        StatusIntEnum,
        default=StatusIntEnum.PENDING_TO_VALIDATE,
        description='0:等待驗證 1:驗證成功 2:驗證失敗 3:需人工',
    )
    sub_status = fields.IntEnumField(
        SubStatusIntEnum,
        default=SubStatusIntEnum.NONE,
        description='子狀態',
    )
    certificate_status = fields.IntEnumField(
        CertificateStatusIntEnum,
        default=CertificateStatusIntEnum.NONE,
        description='是否已送出審核(0:否1:是)',
    )
    expire_time = fields.IntField(default=0)
    created_at = fields.DatetimeField()
    updated_at = fields.IntField()
    created_ip = fields.CharField(max_length=15)

    class Meta:
        table = 'p2p_user`.`user_certification'

    def get_remark_dict(self) -> dict:
        """ 獲取錯誤訊息字典

        Returns:
            dict
        """
        try:
            return json.loads(self.remark)
        except json.JSONDecodeError:
            return {}

    def get_remark_json(self) -> str:
        """ 獲取錯誤訊息 JSON

        Returns:
            str
        """
        remark_dict = self.get_remark_dict()
        return json.dumps(remark_dict, ensure_ascii=False, indent=4)

    def get_content_dict(self) -> dict:
        """ 獲取內容字典

        Returns:
            dict
        """
        return json.loads(self.content)


CONFIG = Config.parse_file(
    Path(__file__).parent / "config.json"
)


async def main():
    await init()

    uc_list = (
        await P2pUserUserCertificationModel.all()
        .filter(
            status=P2pUserUserCertificationModel.StatusIntEnum.SUCCEED,
            certification_id=1,
            created_at__gte=datetime.datetime(2023, 1, 1, 0, 0, 0).timestamp(),
        )
        .filter(
            id__in=[
                259237,
                259587,
                259904,
                259912,
                259927,
                260053,
                260255,
                260109,
            ],
        )
        .limit(100)
    )
    for uc in uc_list:
        content_dict = uc.get_content_dict()
        front_img_url = content_dict['front_image']
        back_img_url = content_dict['back_image']
        healthcard_img_url = content_dict['healthcard_image']
        person_img_url = content_dict['person_image']
        # print(f"{uc.id=}")
        # print(f"{front_img_url=}")
        # print(f"{back_img_url=}")
        # print(f"{healthcard_img_url=}")
        # print(f"{person_img_url=}")
        # break

        out = SelfieVerificationOut.from_image_bytes(
            id_card_image_bytes=Image(url=front_img_url).get_bytes(),
            id_card_back_image_bytes=Image(url=back_img_url).get_bytes(),
            health_card_image_bytes=Image(url=healthcard_img_url).get_bytes(),
            hold_card_selfie_image_bytes=Image(url=person_img_url).get_bytes(),
            strictness_int=2,
        )
        # print()
        if out.err_msg:
            logger.error(f"FAILED: {uc.id=}, {out.err_msg=}")
        else:
            logger.success(f"PASSED: {uc.id=}")


if __name__ == "__main__":
    run_async(main())
