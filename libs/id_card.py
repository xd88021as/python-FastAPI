
import datetime
import re
from typing import Optional, Tuple
from PIL import ImageEnhance
from pydantic import Field, constr, root_validator, validator
from shapely.geometry import Polygon
from libs.household_registration import ApplyCodeIntEnum, IssueSiteIdEnum

from libs.exceptions import IDCardValidationNotPassError, ServerError

from . import google_vison_ocr
from . import household_registration_api
from .household_registration_api import (
    HouseholdRegistrationAPI,
    RdCodeEnum,
    CheckIdCardApplyCodeEnum,
)
from .utils import (
    Image,
    InfoCardBase,
    HasFaceBase,
    BaseModel,
    get_enum_description,
)


class Ocr(BaseModel):
    """ 身分證正面 OCR 辨識結果
    """
    person_id: str | None = Field(
        None,
        description="身分證號碼",
    )
    name: str | None = Field(
        None,
        description="姓名",
    )
    birth_yyy_int: int | None = Field(
        None,
        description="生日日期(民國年)",
    )
    birth_m_int: int | None = Field(
        None,
        description="生日日期(月)",
    )
    birth_d_int: int | None = Field(
        None,
        description="生日日期(日)",
    )
    apply_yyy_int: int | None = Field(
        None,
        description="發證日期(民國年)",
    )
    apply_m_int: int | None = Field(
        None,
        description="發證日期(月)",
    )
    apply_d_int: int | None = Field(
        None,
        description="發證日期(日)",
    )
    apply_code_int: ApplyCodeIntEnum | None = Field(
        None,
        description=get_enum_description(ApplyCodeIntEnum),
    )
    issue_site_id: IssueSiteIdEnum | None = Field(
        None,
        description=get_enum_description(IssueSiteIdEnum),
    )

    @classmethod
    def get_example(cls) -> "Ocr":
        return cls(
            person_id="A123456789",
            name="王小明",
            birth_yyy_int=80,
            birth_m_int=1,
            birth_d_int=1,
            apply_yyy_int=100,
            apply_m_int=1,
            apply_d_int=1,
            apply_code_int=ApplyCodeIntEnum.初發,
            issue_site_id=IssueSiteIdEnum.新北市,
        )


class Verification(BaseModel):
    """ 核實結果
    """
    is_valid_bool: bool = Field(
        True,
        description="資料是否完整且正確",
    )
    err_msg: str = Field(
        "",
        description="錯誤訊息",
    )

    @classmethod
    def get_example(cls) -> "Verification":
        return cls()


class VerifyOut(BaseModel):
    """ 身分證正面辨識與核實結果
    """
    ocr: Ocr
    verification: Verification

    @classmethod
    def get_example(cls) -> "VerifyOut":
        return cls(
            ocr=Ocr.get_example(),
            verification=Verification.get_example(),
        )


FIELDS = {
    "person_id": {"description": "身分證號碼"},
    "name": {"description": "姓名"},
    "birth_yyy": {"description": "生日日期(民國年)"},
    "birth_mm": {"description": "生日日期(月)"},
    "birth_dd": {"description": "生日日期(日)"},
    "apply_yyy": {"description": "發證日期(民國年)"},
    "apply_mm": {"description": "發證日期(月)"},
    "apply_dd": {"description": "發證日期(日)"},
    "apply_code_int": {
        "description": "領補換類別代碼 (" + " / ".join([
            f"{v}: {k}"
            for k, v in household_registration_api.ApplyCodeIntEnum.__members__.items()
        ]) + ")"
    },
    "issue_site_id": {
        "description": "發卡機關代碼 (" + " / ".join([
            f"{v}: {k}"
            for k, v in household_registration_api.IssueSiteIdEnum.__members__.items()
        ]) + ")"
    },
}


class IDCardOcrOut(BaseModel):
    """ 身分證正面 ocr 辨識結果響應
    """
    person_id: str = ""
    name: str = ""
    birth_yyy: str = ""
    birth_mm: str = ""
    birth_dd: str = ""
    apply_yyy: str = ""
    apply_mm: str = ""
    apply_dd: str = ""
    apply_code_int: str = ""
    issue_site_id: str = ""

    class Config:
        fields = FIELDS


class IDCardStrict(IDCardOcrOut):
    """ 身分證正面嚴格資訊模型
    """
    person_id: constr(regex=r"^[a-zA-Z]{1}[0-9]{9}$")
    name: str
    birth_yyy: int
    birth_mm: int
    birth_dd: int
    apply_yyy: int
    apply_mm: int
    apply_dd: int
    apply_code_int: household_registration_api.ApplyCodeIntEnum
    issue_site_id: household_registration_api.IssueSiteIdEnum

    @root_validator
    def validate_apply_and_birth_date(cls, values):
        """ 驗證:發證日期和生日日期
        """
        now_date = datetime.datetime.now().date()
        apply_date = datetime.date(
            values.get("apply_yyy")+1911,
            values.get("apply_mm"),
            values.get("apply_dd"),
        )
        birth_date = datetime.date(
            values.get("birth_yyy")+1911,
            values.get("birth_mm"),
            values.get("birth_dd"),
        )
        assert (birth_date <= apply_date), "發證日期應大於出生日期"
        assert (apply_date <= now_date), "發證日期應小於現在日期"
        return values

    @validator("person_id")
    def validate_person_id(cls, v):
        """ 身分證字大寫，並驗證格式
        """
        return v.upper()

    class Config:
        fields = FIELDS

    def is_householdRegistration_valid(self):
        """ 戶政 API 驗證身分證是否合法

        Raise:
            IDCardValidationNotPassError: 戶政 API 驗證未通過
            ValueError: 連線問題 / 戶政 API 內部錯誤等其他網路錯誤
        """

        # 送出請求並獲取響應
        res: HouseholdRegistrationAPI.Response = HouseholdRegistrationAPI.Request(
            person_id=self.person_id,
            apply_yyy=self.apply_yyy,
            apply_mm=self.apply_mm,
            apply_dd=self.apply_dd,
            apply_code_int=self.apply_code_int.value,
            issue_site_id=self.issue_site_id.value,
        ).send()

        # 若請求網路錯誤
        if res.httpCode != "200":
            raise ServerError(
                f"HTTP Code {res.httpCode}: {res.httpMessage}"
            )
        # 若戶政 API 內部網路錯誤
        if res.rdCode != RdCodeEnum.__members__["查詢作業完成"]:
            # 戶政 API 遇到身分證格式錯誤時，`rdCode` 和 `rdMessage` 會是空字串
            res.rdMessage = res.rdMessage or "格式錯誤"
            raise ServerError(
                f"HouseholdRegistration Server Code {res.rdCode}: {res.rdMessage}")

        # 檢查身分證驗證是否通過
        if res.responseData.checkIdCardApply != CheckIdCardApplyCodeEnum.__members__["國民身分證資料與檔存資料相符"]:
            msg = res.responseData.checkIdCardApply.name if res.responseData.checkIdCardApply else "未知錯誤"
            raise IDCardValidationNotPassError(
                message=(
                    f"{msg}\n"
                    f"IDCard info: {self}"
                )
            )


class IDCard(InfoCardBase, HasFaceBase, IDCardOcrOut):
    """ 身分證正面
    """

    @classmethod
    def from_image(cls, image: Image):
        """ 根據圖片建立實例 (根據 ocr 分析結果)

        Args:
            image (Image): 圖片
        """
        gray_id_card_pilimg = image.pilimg.convert("L")
        enhancer = ImageEnhance.Contrast(gray_id_card_pilimg)
        gray_id_card_pilimg = enhancer.enhance(factor=1.3)
        gray_id_card_image = Image(pilimg=gray_id_card_pilimg)
        imageTextAnnotation = gray_id_card_image.get_imageTextAnnotation()
        # imageTextAnnotation = image.get_imageTextAnnotation()
        instance = cls.from_imageTextAnnotation(imageTextAnnotation)
        instance.image = image
        return instance

    def get_strict(self) -> IDCardStrict:
        """ 獲取身分證正面嚴格資訊模型

        Raises:
            ValidationError: 身分證正面資訊格式錯誤

        Returns:
            IDCardStrict
        """
        return IDCardStrict(**self.dict())

    def __eq__(self, other: "IDCard") -> bool:
        """ 比對 ocr 結果是否相同 (for testing)
        """
        if not isinstance(other, self.__class__):
            return False
        return self.dict(exclude={"_ocr_str"}) == other.dict(exclude={"_ocr_str"})

    def get_apply_yyyy_int(self) -> Optional[int]:
        """ 取得發證發證日期(西元年)

        Returns:
            Optional[int]
        """
        if not self.apply_yyy:
            return None
        return int(self.apply_yyy) + 1911

    @classmethod
    def from_imageTextAnnotation(
            cls,
            imageTextAnnotation:  "google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation") -> "IDCard":
        """ 根據 ocr 分析結果建立實例

        Args:
            imageTextAnnotation (ImageTextAnnotation): ocr 分析結果

        Returns:
            IDCard
        """
        # 獲取圖片 ocr 文字
        ocr_str = imageTextAnnotation.get_ocr_str()
        ocr_str = ocr_str.replace(" ", "")  # 確保輸入文字沒有空白
        # 獲取身分證號
        person_id = cls.get_person_id_from_ocr_str(ocr_str)
        # 獲取姓名 (可能會包含多餘的辨識文字在後面)
        name = cls.get_name_from_imageTextAnnotation(
            imageTextAnnotation=imageTextAnnotation,
        )

        # 獲取生日日期
        birth_yyy, birth_mm, birth_dd = cls.get_birth_date_tuple_from_ocr_str(
            ocr_str
        )
        # 獲取發證日期
        apply_yyy, apply_mm, apply_dd = cls.get_apply_date_tuple_from_ocr_str(
            ocr_str
        )
        # 若 生日日期年分 大於 發證日期年分，則互相調換兩個日期
        if birth_yyy > apply_yyy:
            (
                (birth_yyy, birth_mm, birth_dd),
                (apply_yyy, apply_mm, apply_dd),
            ) = (
                (apply_yyy, apply_mm, apply_dd),
                (birth_yyy, birth_mm, birth_dd),
            )

        # 獲取發證資訊
        apply_info_str = cls.get_apply_info_str_ocr_str(ocr_str)
        # 獲取發證縣市機關代碼
        issue_site_id = cls.get_issue_site_id_from_apply_info_str(
            apply_info_str
        )
        # 獲取領補換類別代碼
        apply_code_int = cls.get_apply_code_int_from_apply_info_str(
            apply_info_str
        )

        return cls(
            img_full_text=ocr_str,
            person_id=person_id,
            name=name,
            apply_yyy=apply_yyy,
            apply_mm=apply_mm,
            apply_dd=apply_dd,
            birth_yyy=birth_yyy,
            birth_mm=birth_mm,
            birth_dd=birth_dd,
            issue_site_id=issue_site_id,
            apply_code_int=apply_code_int
        )

    @staticmethod
    def get_person_id_from_ocr_str(ocr_str: str) -> str:
        """ 獲取身分證號

        Args:
            ocr_str (str): 圖片文字

        Returns:
            str: 身分證號
        """

        # 獲取長度為 10 的身分證號
        ocr_line_str_list = [
            re.sub(r"[^a-zA-Z0-9$]", "", line_str) for line_str in ocr_str.split("\n")
        ]
        ocr_line_str_list = [
            line_str for line_str in ocr_line_str_list
            if len(line_str) == 10
        ]
        for ocr_line_str in ocr_line_str_list:
            for person_id in re.findall(r"[A-Z01$]\d{9}", ocr_line_str):
                # 修正開頭英文字母被誤認為數字: 數字0 → 英文O / 數字1 → 英文I
                if person_id.startswith("0"):
                    person_id = "O" + person_id[1:]
                elif person_id.startswith("1"):
                    person_id = "I" + person_id[1:]
                elif person_id.startswith("$"):
                    person_id = "S" + person_id[1:]
                return person_id

        return ""

    @staticmethod
    def get_name_from_imageTextAnnotation(imageTextAnnotation:  "google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation") -> str:
        """ 獲取姓名

        Args:
            imageTextAnnotation (
                google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation)

        Returns:
            str
        """
        # 異體字替換
        variant_character_mapping_dict = {
            '黄': '黃',
        }

        def get_variant_character_replaced_name(name: str) -> str:
            for variant_character, standard_character in variant_character_mapping_dict.items():
                name = name.replace(variant_character, standard_character)
            return name

        # 獲取 OCR 字串
        ocr_str = imageTextAnnotation.get_ocr_str()
        # 削去非中文字元 (但不消去換行字元)
        ocr_str = re.sub(r"[^\u4e00-\u9fa5\n]", "", ocr_str)

        # 替換掉非中文的字元
        ch_with_linbreak_ocr_str = re.sub(r"[^\u4e00-\u9fa5\n]", "", ocr_str)
        # 去除開頭有身分證欄位關鍵字的行字串
        name_ocr_line_str_list = [
            line_str.strip()
            for line_str in ch_with_linbreak_ocr_str.split("\n")
            # 不含任何欄位關鍵字
            if line_str.strip() and not any([
                line_str.strip().startswith(col_kw)
                for col_kw in [
                    "中華",
                    "出生",
                    "年月",
                    "民國",
                    "發證",
                    "統",
                    "僅供",
                    "僅限",
                ]
            ])
        ]

        # 策略1: 若某行開頭為姓名，且後面中文字達到 3 個，則為姓名
        for line_str in name_ocr_line_str_list:
            if line_str.startswith('姓名') and len(line_str) == 5:
                return get_variant_character_replaced_name(line_str[2:])

        # 策略2: 使用「中華民國」的長寬作為單位向量，獲取「姓名」欄位右側的區域
        roc_col_textBox = imageTextAnnotation.get_textBox(
            startswith="中華民",
        )
        name_col_textBox = imageTextAnnotation.get_textBox(
            startswith="姓名",
        )

        # 確認必要的文字框皆存在
        if not all([
                roc_col_textBox,
                name_col_textBox, ]):
            return ""

        col_i_arr = roc_col_textBox.right_bottom - roc_col_textBox.left_bottom
        col_j_arr = roc_col_textBox.left_bottom - roc_col_textBox.left_top
        name_polygon_origin_point = name_col_textBox.center - col_j_arr
        name_polygon = Polygon(
            [
                name_polygon_origin_point,
                name_polygon_origin_point + col_i_arr*3.1,
                name_polygon_origin_point + col_i_arr*3.1 + col_j_arr*2,
                name_polygon_origin_point + col_j_arr*2,
            ]
        )
        # 獲取姓名
        name = imageTextAnnotation.get_ocr_str_in_polygon(
            polygon=name_polygon,
            i_arr=col_i_arr,
        )
        # 消除非中文字元
        name = re.sub(r"[^\u4e00-\u9fa5]", "", name)
        # 去掉誤判亮紋為文字
        if name.endswith("目"):
            name = name[:-1]
        elif name.endswith("自"):
            name = name[:-1]

        # 去掉開頭的「姓名」多餘的文字
        if name.startswith("姓名"):
            name = name[2:]
        elif name.startswith("名"):
            name = name[1:]

        return get_variant_character_replaced_name(name)

    @staticmethod
    def get_birth_date_tuple_from_ocr_str(ocr_str: str) -> Tuple[int, int, int]:
        """ 獲取生日日期

        Args:
            ocr_str (str): 圖片文字

        Returns:
            Tuple[int, int, int]: 生日日期
        """
        # 設置匹配模式: 獲取文本中第一個符合民國年.月.日的日期格式
        pattern = r"\D(?P<birth_yyy>\d{2,3})年(?P<birth_mm>\d+)月(?P<birth_dd>\d+)"
        match = re.search(pattern, ocr_str)
        if not match:
            return ("", "", "")

        return (
            int(match.group("birth_yyy")),
            int(match.group("birth_mm")),
            int(match.group("birth_dd")),
        )

    @staticmethod
    def get_apply_date_tuple_from_ocr_str(ocr_str: str) -> Tuple[int, int, int]:
        """ 獲取發證日期

        Args:
            ocr_str (str): 圖片文字

        Returns:
            Tuple[int, int, int]: 發證日期 (yyy, mm, dd), 其中 yyy 為民國年
        """

        # 設置匹配模式: 獲取文本中最後一個符合民國年.月.日的日期格式
        pattern = r"\D(?P<apply_yyy>\d{2,3})年(?P<apply_mm>\d+)月(?P<apply_dd>\d+)"
        match = None
        for match in re.finditer(pattern, ocr_str):
            pass
        if not match:
            return ("", "", "")
        return (
            int(match.group("apply_yyy")),
            int(match.group("apply_mm")),
            int(match.group("apply_dd")),
        )

    @staticmethod
    def get_apply_info_str_ocr_str(ocr_str: str) -> str:
        """ 獲取發證資訊文字

        Args:
            ocr_str (str): 圖片文字

        Returns:
            str: 發證資訊文字, 例如: ``(新北市)補發``
        """
        # 設置匹配模式: 獲取於「發證資訊」文字以前的文字
        pattern = r"(?P<apply_info>\(\w{2,3}\)[初補換换])"
        match = re.search(pattern, ocr_str)
        if not match:
            return ""
        return match.group("apply_info")

    @staticmethod
    def get_issue_site_id_from_apply_info_str(apply_info_str: str) -> str:
        """ 獲取發證縣市機關代碼

        Args:
            apply_info_str (str): 發證資訊文字, 例如: ``(新北市)補發``

        Returns:
            str: 發證機關代碼
        """

        for issue_site_id, issue_site_str in household_registration_api.ISSUE_SITE_ID_AND_STR_MAPPING.items():
            if issue_site_str in apply_info_str:
                return issue_site_id

        # 若找不到就報錯
        return ""

    @staticmethod
    def get_apply_code_int_from_apply_info_str(apply_info_str: str) -> int:
        """ 獲取領補換類別代碼

        Args:
            apply_info_str (str): 發證資訊文字, 例如: ``(新北市)補發``

        Returns:
            int: 領補換類別代碼 (1:初發 / 2:補發 / 3:換發)
        """
        # 領補換類別關鍵字與代碼對照表字典
        apply_info_kw_and_code_int_mapping = {
            "初": 1,
            "補": 2,
            "換": 3,
            "换": 3,
        }
        for apply_info_kw, apply_code_int in apply_info_kw_and_code_int_mapping.items():
            if apply_info_kw in apply_info_str:
                return apply_code_int

        # 若找不到領補換類別的關鍵字就報錯
        return ""

    def check_info_validity(self) -> None:
        """ 辨識身分證是否正確

        Raises:
            IDCardValidationNotPass: 身分證驗證不通過
            HttpError: 網路連線等其他錯誤
        """
        HouseholdRegistrationAPI.check_idCard_info_validity(
            person_id=self.person_id,
            apply_yyy=self.apply_yyy,
            apply_mm=self.apply_mm,
            apply_dd=self.apply_dd,
            issue_site_id=self.issue_site_id,
            apply_code_int=self.apply_code_int,
        )
