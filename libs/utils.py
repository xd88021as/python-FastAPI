import PIL.Image
import requests
import base64
import re
import importlib
import datetime
import pandas as pd
from io import BytesIO
from abc import ABC, abstractmethod
from enum import Enum, IntEnum
from typing import Type
from pathlib import Path
from loguru import logger
from typing import TYPE_CHECKING, List, Any
from typing_extensions import Literal

from pydantic import BaseModel
if TYPE_CHECKING:
    from libs.google_vison_ocr import GoogleVisonOCR


def get_enum_description(enum_cls: Type[Enum]) -> str:
    """ 取得 Enum 的描述
    """
    return enum_cls.__doc__ + "\n" + "\n\n".join(
        f"- {enum.value}: {enum.name}\n"
        for enum in enum_cls
    )


def get_example_201_responses_dict(example: BaseModel | dict) -> dict:
    """ 取得 201 response 的 example
    """
    return {
        201: {"content": {"application/json": {"example": example}}},
    }


def get_example_200_responses_dict(example: BaseModel | dict) -> dict:
    """ 取得 200 response 的 example
    """
    return {
        200: {"content": {"application/json": {"example": example}}},
    }


class Config(BaseModel):
    """ 設定檔模型 (config.json)
    """

    class Azure(BaseModel):
        endpoint: str
        subscription_key: str

    class Encryption(BaseModel):
        class Rsa(BaseModel):
            mode: Literal["pkcs1", "pkcs8"] = "pkcs8"

        class Aes(BaseModel):
            key: str
            iv: str
        rsa: Rsa
        aes: Aes

    class Face8(BaseModel):
        api_key: str
        api_secret: str

    class Faceplusplus(BaseModel):
        api_key: str
        api_secret: str

    class GoogleVisonOcr(BaseModel):
        api_key: str

    class HouseholdRegistrationApi(BaseModel):
        enabled: bool
        org_id: str
        ap_id: str
        iss: str
        apache_ip: str
        apache_port: int

        class Config:
            fields = {
                "enabled": {"description": "是否啟用戶役政驗證功能."},
                "org_id": {"description": "營利事業登記證號, 8 碼"},
                "ap_id": {"description": "內政部配賦之公司(企業)帳號, 最長 5 碼"},
                "iss": {"description": "內政部配賦之 iss key"},
                "apache_ip": {"description": "Apache IP"},
                "apache_port": {"description": "Apache Port"},
            }

    class Jwt(BaseModel):
        key: str

    class MongoDB(BaseModel):
        host: str
        port: int
        username: str
        password: str
        database: str

    azure: Azure
    encryption: Encryption
    face8: Face8
    faceplusplus: Faceplusplus
    google_vison_ocr: GoogleVisonOcr
    household_registration_api: HouseholdRegistrationApi
    jwt: Jwt
    mongo_db: MongoDB

    _CONFIG = None

    @classmethod
    def get(cls, json_path=Path(__file__).parent.parent / "config.json"):
        if cls._CONFIG is None:
            cls._CONFIG = cls.parse_file(json_path)
        return cls._CONFIG


class Image:
    """ 圖片類
    """

    def __init__(
        self,
        url: str = None,
        path: Path = None,
        path_str: str = None,
        bytes_: bytes = None,
        base64str: str = None,
        pilimg: PIL.Image.Image = None,
    ):
        """ 初始化

        Raises:
            PIL.Image.DecompressionBombError: 圖片壓縮超過限制

        Args:
            url (str, optional): 圖片網址. Defaults to None.
            path (Path, optional): 圖片路徑. Defaults to None.
            path_str (str, optional): 圖片路徑字串. Defaults to None.
            bytes_ (str, optional): 圖片 bytes. Defaults to None.
            base64str (str, optional): 圖片 base64 字串. Defaults to None.

        """

        assert any([
            url,
            path,
            path_str,
            bytes_,
            base64str,
            pilimg,
        ]), "請輸入圖片的路徑、圖片的 base64 字串、圖片 bytes 或圖片的路徑字串"

        self.pilimg = None
        self.path = path or (Path(path_str) if path_str else None)
        self.url = url

        self._base64str = None
        self._bytes = None
        self._ocr_str = None

        if self.path:
            assert self.path.exists(), "請確認圖片路徑是否存在"

        # 用各種方式建立 Pillow 圖片
        # 若圖片來源為 url
        if url:
            response = requests.get(url)
            self.pilimg = PIL.Image.open(BytesIO(response.content))
        # 若圖片來源為路徑
        elif self.path:
            self.pilimg = PIL.Image.open(self.path)
        # 若圖片來源為 base64 字串
        elif base64str:
            base64_data = re.sub("^data:image/.+;base64,", "", base64str)
            byte_data = base64.b64decode(base64_data)
            image_data = BytesIO(byte_data)
            self.pilimg = PIL.Image.open(image_data)
        elif bytes_:
            self.pilimg = PIL.Image.open(BytesIO(bytes_))
        elif pilimg:
            self.pilimg = pilimg

        # 壓縮 Pillow 圖片大小至 3000 x 3000 像素
        # 若圖片太大會觸發錯誤: `PIL.Image.DecompressionBombError`
        # self.pilimg.thumbnail((3000, 3000))

    def get_bytes(self) -> bytes:
        # 若之前曾取過 base64 字串，則直接回傳上次的結果
        if self._bytes:
            return self._bytes

        # 從 Pillow 圖片取得 base64 字串
        byte_data = BytesIO()
        self.pilimg.save(byte_data, format=self.pilimg.format or "JPEG")
        byte_data.seek(0)
        return byte_data.read()

    def get_base64str(self, format: str = "JPEG") -> str:
        """ 取得圖片的 base64 字串

        Args:
            format (str, optional): 圖片格式. Defaults to "JPEG".

        Returns:
            str: 圖片 base64 字串
        """
        # 若之前曾取過 base64 字串，則直接回傳上次的結果
        if self._base64str:
            return self._base64str

        self._base64str = base64.b64encode(
            self.get_bytes()
        ).decode("utf-8")
        return self._base64str

    def get_textDetectionRequests(self) -> "GoogleVisonOCR.TextDetectionRequests":
        """ 取得 Google Vision OCR 的分析請求實例

        Returns:
            GoogleVisonOCR.TextDetectionRequests
        """
        from .google_vison_ocr import GoogleVisonOCR
        return GoogleVisonOCR.TextDetectionRequests(
            requests=[
                (
                    # 請求 img_base64str 取得 ocr 文字
                    GoogleVisonOCR.TextDetectionRequest.from_img_base64str(
                        img_base64str=self.get_base64str()
                    )
                )
            ]
        )

    def get_ocr_str(self) -> str:
        """ 獲取輸入圖片的 OCR 文字 (同時設定屬性 self.get_ocr_str)

        Returns:
            str: OCR 文字
        """
        if self._ocr_str:
            return self._ocr_str

        # 獲取 ocr 分析請求實例
        textDetectionRequests = self.get_textDetectionRequests()
        # 獲取批次分析結果的第一個請求結果 (因為只有一個請求)
        self._ocr_str = textDetectionRequests.get_ocr_str_list()[0]

        return self._ocr_str

    def get_imageTextAnnotation(self) -> "GoogleVisonOCR.ImageTextAnnotation":
        """
        獲取輸入圖片的 OCR 分析結果

        Raises:
            requests.exceptions.HTTPError: 網路連線問題

        Returns:
            GoogleVisonOCR.ImageTextAnnotation: OCR 分析結果
        """

        # 獲取 ocr 分析請求實例
        textDetectionRequests = self.get_textDetectionRequests()
        imageTextAnnotation_list = textDetectionRequests.get_imageTextAnnotation_list()
        # 返回第一個請求結果 (因為只有一個請求)
        return imageTextAnnotation_list[0]


class FaceBase(BaseModel, ABC):
    """ 人臉基底類
    """
    @classmethod
    @abstractmethod
    def get_face_list_from_image(
        cls,
        image: Image,
    ) -> List["FaceBase"]:
        """ 自圖片建立 Face 實例串列

        Args:
            image (Image): 圖片

        Raises:
            requests.exceptions.HTTPError: 網路連線問題

        Returns:
            List["FaceBase"]
        """
        pass

    @classmethod
    def compare_face(
        cls,
        face: "FaceBase",
    ) -> float:
        """ 比較與另一個 FaceBase 之間的相似度

        Args:
            face (FaceBase): 另一個比較的臉

        Raises:
            requests.exceptions.HTTPError: 網路連線問題

        Returns:
            float
        """
        pass


class HasFaceBase(BaseModel):
    """ 含有臉的文件基底類 (例如: 身分證正面、持證自拍照)

    Attributes:
        image (Image): 圖片
        faceplusplus_face_list (List[Faceplusplus.Face]): Face++ 的臉列表
        face8_face_list (List[Face8.Face]): Face8 的臉列表
        azure_face_list (List[Azure.Face]): Azure 的臉列表

    """
    from .azure import Azure
    from .face8 import Face8
    from .faceplusplus import Faceplusplus

    faceplusplus_face_list: List[Faceplusplus.Face] = None
    face8_face_list: List[Face8.Face] = None
    azure_face_list: List[Azure.Face] = None
    image: Any = None

    @classmethod
    def from_image(cls, image: Image):
        """ 根據圖片建立實例

        Args:
            image (Image): 圖片
        """
        instance = cls()
        instance.image = image
        return instance

    def get_face_list(
            self,
            face_recognition_server_name: Literal[
                "Faceplusplus",
                "Face8",
                "Azure",
            ],) -> List["FaceBase"]:
        """ 獲取 Face 的臉列表

        Args:
            face_recognition_server_name (Literal[
                "Faceplusplus",
                "Face8",
                "Azure",
            ]): Face++, Face8, Azure 的臉辨識伺服器名稱

        Returns:
            List[FaceBase]
        """

        # 獲取指定的 Face class 類
        Face: FaceBase = getattr(
            importlib.import_module(
                f"libs.{face_recognition_server_name.lower()}"
            ), face_recognition_server_name
        ).Face

        # 獲取該 Face class 類對應的臉列表 field 名稱，例如：`faceplusplus_face_list`
        face_list_field_name = f"{face_recognition_server_name.lower()}_face_list"

        # 若之前已經獲取過臉列表，則直接回傳，否則生成臉列表後再回傳
        setattr(
            self,
            face_list_field_name,
            (
                getattr(self, face_list_field_name)
                or Face.get_face_list_from_image(self.image)
            )
        )
        return getattr(self, face_list_field_name)


class InfoCardBase(BaseModel):
    """ 證件基底類
    """
    image: Any = None

    # class Config:
    #     arbitrary_types_allowed = True

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.dict(exclude={"image"}) == other.dict(exclude={"image"})

    @classmethod
    def from_imageTextAnnotation(
            cls,
            imageTextAnnotation: "GoogleVisonOCR.ImageTextAnnotation",):
        """ 根據 ocr 分析結果建立實例

        Args:
            imageTextAnnotation (ImageTextAnnotation): ocr 分析結果

        """
        pass

    @classmethod
    def from_image(cls, image: Image):
        """ 根據圖片建立實例 (根據 ocr 分析結果)

        Args:
            image (Image): 圖片
        """

        imageTextAnnotation = image.get_imageTextAnnotation()
        instance = cls.from_imageTextAnnotation(imageTextAnnotation)
        instance.image = image
        return instance

    @classmethod
    def create_excel_file(cls, img_dir_path: Path):
        """ 從 身分證反面圖片資料夾 建立 excel 檔 (for testing)

        Args:
            img_dir_path (str): 圖片資料夾路徑
        """
        log_width = 80

        # 獲取每張健保卡圖片路徑串列: 根據樣本編號排序
        img_path_list = sorted(
            list(img_dir_path.glob("*.jpg")),
            key=lambda x: int(x.stem.split("_")[-1])
        )

        # 遍歷每張圖片
        df_row_dict_list = []
        for img_path in img_path_list[:]:

            print("img_path:", img_path.name)
            imgage = Image(
                path=img_path
            )
            imageTextAnnotation = imgage.get_imageTextAnnotation()
            ocr_str = imageTextAnnotation.get_ocr_str()

            print("ocr_str".center(log_width, "-"))
            print(ocr_str)

            # 嘗試從 ocr 獲取欄位資訊
            instance = cls.from_imageTextAnnotation(
                imageTextAnnotation=imageTextAnnotation
            )
            print("instance".center(log_width, "-"))
            print(instance)
            print()

            # 建立 DF 單 row 資料字典
            df_row_dict = {
                # 圖片檔名
                "img_path": img_path.name,
                # 圖片 OCR 文字
                "ocr_str": ocr_str,

                # 資料內容
                **instance.dict(),
                # 分析限制欄位(手動人工輸入)
                "limit": "",
            }

            # 植入 imageTextAnnotation OCR辨識結果實例 json str 至一欄或多個欄位
            # 每個 cell 的字串上限為 32,767 字元，故超過時會拆成多個 cell
            imageTextAnnotation_json_str = imageTextAnnotation.json()
            chunks, chunk_size = len(imageTextAnnotation_json_str), 30000
            for chunk_i, str_i in enumerate(range(0, chunks, chunk_size)):
                df_row_dict[f"imageTextAnnotation_json_str_{chunk_i}"] = imageTextAnnotation_json_str[str_i:str_i+chunk_size]

            df_row_dict_list.append(df_row_dict)

        # 輸出 csv 檔
        df = pd.DataFrame(
            df_row_dict_list,
        )
        df.to_excel(
            # 建立 csv 檔案，範例: IDCard_220128_121733.xlsx
            (
                img_dir_path /
                f'{cls.__name__}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            ),
            index=False,
            encoding="utf-8-sig",
        )

    @classmethod
    def test_excel_file(
        cls,
        img_dir_path: Path,
        log_width=80,
        pass_ratio_threshold=0.8,
    ):
        """ 測試 excel 檔

        Args:
            img_dir_path (str): 圖片資料夾路徑.
            log_width (int): log 寬度. Default: 80.
            pass_ratio_threshold (float): 通過率門檻. Default: 0.8.

        """
        from .google_vison_ocr import GoogleVisonOCR

        # 設定 log 檔名與位置，並先清空內容
        log_path = Path("log/test_excel_file.log")
        # 清空檔案內容
        log_path.write_text("")

        logger.add(
            # log 檔案位置
            log_path,
            # 是否紀錄完整錯誤訊息 (選 False 較為簡潔)
            backtrace=False,
            encoding="utf-8",
            level="DEBUG",
        )

        excel_path = next(
            img_dir_path.glob("*.xlsx"), None
        )
        assert excel_path is not None, "沒有找到測試資料 xlsx 檔案"
        # 獲取測試樣本 DF 資料表
        df = pd.read_excel(
            excel_path,
            # 必須有以下欄位
            dtype=str,
        ).fillna("")

        # 遍歷測試樣本 DF 資料表的 row
        failed_count = 0
        for _, row_dict in df.iterrows():
            logger.info(f"{row_dict['img_path']}")

            # 獲取 ocr 字串
            ocr_str = row_dict["ocr_str"]

            # 獲取 ocr 解析結果 imageTextAnnotation 實例: 解析一欄或多欄位的 json 字串
            imageTextAnnotation_json_str: str = "".join([
                _imageTextAnnotation_json_str
                for imageTextAnnotation_json_str_col_name in sorted([
                    row_dict_key
                    for row_dict_key in row_dict.keys()
                    if row_dict_key.startswith("imageTextAnnotation_json_str")
                ])
                for _imageTextAnnotation_json_str in row_dict[imageTextAnnotation_json_str_col_name]
            ])
            imageTextAnnotation = GoogleVisonOCR.ImageTextAnnotation.parse_raw(
                imageTextAnnotation_json_str.replace("\n", "\\n")
            )

            # 猜測的實例: 經 ocr 分析後生成的實例
            guess_instance = cls.from_imageTextAnnotation(
                imageTextAnnotation
            )
            # 正確實例
            correct_instance = cls(
                **row_dict
            )
            # 若辨識結果不同
            if (guess_instance != correct_instance):
                failed_count += 1
                # 若沒 ocr 解析上的限制理由，則印出差異
                if not row_dict["limit"]:
                    logger.info(f"img_path: {row_dict['img_path']}")
                    logger.info("ocr_str".center(log_width, "-"))
                    logger.info(ocr_str)
                    logger.info("guess_instance".center(log_width, "-"))
                    logger.info(guess_instance.json(
                        indent=4, ensure_ascii=False))
                    logger.info("correct_instance".center(log_width, "-"))
                    logger.info(correct_instance.json(
                        indent=4, ensure_ascii=False))
                    logger.info("\n")
                else:
                    logger.warning(f"ocr 限制理由: {row_dict['limit']}")

        pass_count = len(df) - failed_count
        pass_ratio = pass_count / len(df)
        pass_bool = (pass_ratio > pass_ratio_threshold)

        if pass_bool:
            logger.info(f"正確捕獲資訊比例為 {pass_ratio:.4f}")
        else:
            msg = f"正確捕獲資訊比例不及標準，應小於 {pass_ratio_threshold }，現在為 {pass_ratio:.4f}"
            logger.error(msg)
            raise AssertionError(msg)


class StrictnessIntEnum(IntEnum):
    """ 嚴謹度
    """
    LOW = 1
    MEDIUM = 2
    HIGH = 3


# 台灣常見姓氏 # TODO: 可參考 ocr repo 進行更新
TAWIWAN_COMMON_SURNAME_LIST = [
    "陳", "林", "黃", "張", "李", "王", "吳", "劉", "蔡", "楊", "許", "鄭",
    "謝", "洪", "郭", "邱", "曾", "廖", "賴", "徐", "周", "葉", "蘇", "莊",
    "呂", "江", "何", "蕭", "羅", "高", "潘", "簡", "朱", "鍾", "游", "彭",
    "詹", "胡", "施", "沈", "余", "盧", "梁", "趙", "顏", "柯", "翁", "魏",
    "孫", "戴", "范", "方", "宋", "鄧", "杜", "傅", "侯", "曹", "薛", "丁",
    "卓", "阮", "馬", "董", "温", "唐", "藍", "石", "蔣", "古", "紀", "姚",
    "連", "馮", "歐", "程", "湯", "黄", "田", "康", "姜", "白", "汪", "鄒",
    "尤", "巫", "鐘", "黎", "涂", "龔", "嚴", "韓", "袁", "金", "童", "陸",
    "夏", "柳", "凃", "邵", "錢", "伍", "倪", "溫", "于", "譚", "駱", "熊",
    "任", "甘", "秦", "顧", "毛", "章", "史", "官", "萬", "俞", "雷", "粘",
    "饒", "張簡", "闕", "凌", "崔", "尹", "孔", "歐陽", "辛", "武", "辜",
    "陶", "易", "段", "龍", "韋", "葛", "池", "孟", "褚", "殷", "麥", "賀",
    "賈", "莫", "文", "管", "關", "向", "包", "丘", "梅", "范姜", "華", "利",
    "裴", "樊", "房", "全", "佘", "左", "花", "魯", "安", "鮑", "郝", "穆",
    "塗", "邢", "蒲", "成", "谷", "常", "閻", "練", "盛", "鄔", "耿", "聶",
    "符", "申", "祝", "繆", "陽", "解", "曲", "岳", "齊", "籃", "應", "單",
    "舒", "畢", "喬", "龎", "翟", "牛", "鄞", "留", "季", "覃", "卜", "項",
    "凃", "喻", "商", "滕", "焦", "車", "買", "虞", "苗", "戚", "牟", "雲",
    "巴", "力", "艾", "樂", "臧", "司", "樓", "費", "屈", "宗", "幸", "衛",
    "尚", "靳", "祁", "諶", "桂", "沙", "欒", "宮", "路", "刁", "時", "龐", "瞿"


]
