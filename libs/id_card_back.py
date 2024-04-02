from pydantic import BaseModel, Field, constr
from shapely.geometry import Polygon
import re

from .utils import (
    InfoCardBase,
)
from . import google_vison_ocr
from libs.id_card import Verification


# 身分證反面上的九種役別 # REF. http://old.ltn.com.tw/2002/new/oct/28/today-p10.htm
MILITARY_ENUM_STR_SET = {
    "常兵備役",
    "常士備役",
    "常官備役",
    "替代備役",
    "預官",
    "預士",
    "國民兵",
    "補充兵",
    "停役兵",
}


FIELDS = {
    "father_name": {"description": "父親姓名"},
    "mother_name": {"description": "母親姓名"},
    "spouse_name": {"description": "配偶姓名"},
    "military": {
        "description": f"役別 ({' / '.join(MILITARY_ENUM_STR_SET)})",
    },
    "birth_address": {"description": "出生地址"},
    "residence_address": {"description": "居住地址"},
    "serial_code": {"description": "流水號"},
}


class Ocr(BaseModel):
    """ 身分證背面 OCR 辨識結果
    """
    father_name: str | None = Field(
        None,
        description="父親姓名",
    )
    mother_name: str | None = Field(
        None,
        description="母親姓名",
    )
    spouse_name: str | None = Field(
        None,
        description="配偶姓名",
    )
    military: str | None = Field(
        None,
        description=(
            "役別 ({military_enum_str_set_str})".format(
                military_enum_str_set_str=", ".join(MILITARY_ENUM_STR_SET),
            )
        ),
    )
    birth_address: str | None = Field(
        None,
        description="出生地址",
    )
    residence_address: str | None = Field(
        None,
        description="居住地址",
    )
    serial_code: str | None = Field(
        None,
        description="流水號",
    )

    @classmethod
    def get_example(cls) -> "Ocr":
        return cls(
            father_name="王大明",
            mother_name="林大美",
            spouse_name="李小美",
            military="常兵備役",
            birth_address="臺灣省嘉義市",
            residence_address="臺北市中正區OO里XX鄰",
            serial_code="1234567890",
        )


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


class IDCardBackOcrOut(BaseModel):
    """ 身分證反面 ocr 辨識結果響應
    """
    father_name: str = ""
    mother_name: str = ""
    spouse_name: str = ""
    military: str = ""
    birth_address: str = ""
    residence_address: str = ""
    serial_code: str = ""

    class Config:
        fields = FIELDS


class IDCardBackStrict(IDCardBackOcrOut):
    """ 身分證反面嚴格資訊模型
    """
    birth_address: str
    residence_address: str
    serial_code: constr(regex=r"^[0-9]{10}$")


class IDCardBack(InfoCardBase, IDCardBackOcrOut):
    """ 身分證反面
    """

    def get_strict(self) -> IDCardBackStrict:
        """ 獲取身分證反面嚴格資訊模型

        Raises:
            ValidationError: 身分證反面資訊格式錯誤

        Returns:
            IDCardBackStrict
        """
        return IDCardBackStrict(**self.dict())

    def __eq__(self, other: "IDCardBack") -> bool:
        """ 比對 ocr 結果是否相同 (for testing)
        """
        if not isinstance(other, self.__class__):
            return False
        return self.dict(exclude={"image"}) == other.dict(exclude={"image"})

    @classmethod
    def from_imageTextAnnotation(
            cls,
            imageTextAnnotation: "google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation",) -> "IDCardBack":
        """ 根據 ocr 分析結果建立實例

        Args:
            imageTextAnnotation (ImageTextAnnotation): ocr 分析結果

        Returns:
            IDCardBack
        """
        # 獲取 ocr 文字 # 去除空白字元
        ocr_str = imageTextAnnotation.get_ocr_str().replace(" ", "")
        # 獲取父母姓名
        father_name = cls.get_father_name_from_imageTextAnnotation(
            imageTextAnnotation)
        mother_name = cls.get_mother_name_from_imageTextAnnotation(
            imageTextAnnotation)
        # 獲取配偶姓名
        spouse_name = cls.get_spouse_name_from_imageTextAnnotation(
            imageTextAnnotation)
        # 獲取役別
        military = cls.get_military_from_ocr_str(ocr_str)
        # 獲取出生地址
        birth_address = cls.get_birth_address_from_ocr_str(ocr_str)
        # 獲取居住地址
        residence_address = cls.get_residence_address_from_ocr_str(ocr_str)
        # 獲取流水號
        serial_code = cls.get_serial_code_from_imageTextAnnotation(
            imageTextAnnotation)

        return cls(
            father_name=father_name,
            mother_name=mother_name,
            spouse_name=spouse_name,
            military=military,
            birth_address=birth_address,
            residence_address=residence_address,
            serial_code=serial_code,
        )

    @staticmethod
    def get_father_name_from_imageTextAnnotation(imageTextAnnotation:  "google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation") -> str:
        """ 獲取父親名字

        Args:
            imageTextAnnotation (
                google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation)

        Returns:
            str
        """
        # 獲取 OCR 字串
        ocr_str = imageTextAnnotation.get_ocr_str()
        # 削去非中文字元 (但不消去換行字元)
        ocr_str = re.sub(r"[^\u4e00-\u9fa5\n]", "", ocr_str)

        # 策略1: 直接解析「父XXX母XXX」的文字
        for ocr_line_str in ocr_str.split("\n"):
            # 獲取「父」和「母」之間的文字
            for father_name_str in re.findall(r"父(.*)母", ocr_line_str):
                if len(father_name_str) == 3:
                    return father_name_str

        # 策略2: 建立錨點，偵測特定欄位文字位置
        # 先獲取「配偶」文字框頂點位置點
        spouse_col_textBox = imageTextAnnotation.get_textBox(
            startswith="配",
        )
        # 獲取「役別」文字框頂點位置點
        military_col_textBox = imageTextAnnotation.get_textBox(
            startswith="役",
        )
        # 獲取「住址」文字框頂點位置點
        address_col_textBox = imageTextAnnotation.get_textBox(
            startswith="住",
        )

        # 確認必要的文字框皆存在
        if not all([
                spouse_col_textBox,
                military_col_textBox,
                address_col_textBox, ]):
            return ""

        # 欄位的單位向量
        col_i_arr = military_col_textBox.get_vertice_point("left_top")\
            - spouse_col_textBox.get_vertice_point("right_top")
        col_j_arr = address_col_textBox.get_vertice_point("left_top")\
            - spouse_col_textBox.get_vertice_point("left_top")

        # 父親欄位的左上位置點
        father_col_lefttop_point = spouse_col_textBox.get_vertice_point("right_top")\
            - col_j_arr
        # 父親欄位文字的區域
        father_name_polygon = Polygon(
            [
                father_col_lefttop_point,
                father_col_lefttop_point + col_i_arr,
                father_col_lefttop_point + col_i_arr + col_j_arr,
                father_col_lefttop_point + col_j_arr,
            ]
        )
        # 獲取父親名字
        father_name = imageTextAnnotation.get_ocr_str_in_polygon(
            polygon=father_name_polygon,
            i_arr=col_i_arr,
        )
        # 消除非中文字元
        father_name = re.sub(r"[^\u4e00-\u9fa5]", "", father_name)

        # 確保長度正確 (沒有父親時會顯示一條線，父親名字可能會被誤判為「一」)
        if len(father_name) == 1:
            return ""

        return father_name

    @staticmethod
    def get_mother_name_from_imageTextAnnotation(imageTextAnnotation:  "google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation") -> str:
        """ 獲取母親名字

        Args:
            imageTextAnnotation (
                google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation)

        Returns:
            str
        """
        # 獲取 OCR 字串
        ocr_str = imageTextAnnotation.get_ocr_str()
        # 削去非中文字元 (但不消去換行字元)
        ocr_str = re.sub(r"[^\u4e00-\u9fa5\n]", "", ocr_str)

        # 策略1: 直接解析「父XXX母XXX」的文字
        for ocr_line_str in ocr_str.split("\n"):
            # 獲取「父」和「母」之間的文字
            for _, mother_name_str in re.findall(r"父(.*)母(.*)", ocr_line_str):
                if len(mother_name_str) == 3:
                    return mother_name_str

        # 建立錨點，偵測特定欄位文字位置
        # 先獲取「配偶」文字框頂點位置點
        spouse_col_textBox = imageTextAnnotation.get_textBox(
            startswith="配",
        )
        # 獲取「役別」文字框頂點位置點
        military_col_textBox = imageTextAnnotation.get_textBox(
            startswith="役",
        )
        # 獲取「住址」文字框頂點位置點
        address_col_textBox = imageTextAnnotation.get_textBox(
            startswith="住",
        )

        # 若找不到「配偶」文字框頂點位置點，則直接透過定位「出生地」來猜測
        spouse_col_lefttop_point = None
        spouse_col_righttop_point = None
        if (spouse_col_textBox is None) and (address_col_textBox is not None):
            birth_address_col_textBox = imageTextAnnotation.get_textBox(
                startswith="出生地",
            )
            up_shift_arr = birth_address_col_textBox.get_vertice_point("left_top")\
                - address_col_textBox.get_vertice_point("left_top")
            spouse_col_lefttop_point = birth_address_col_textBox.get_vertice_point("left_top")\
                + up_shift_arr
            spouse_col_righttop_point = birth_address_col_textBox.get_vertice_point("right_top")\
                + up_shift_arr
        elif spouse_col_textBox:
            spouse_col_lefttop_point = spouse_col_textBox.get_vertice_point(
                "left_top")
            spouse_col_righttop_point = spouse_col_textBox.get_vertice_point(
                "right_top")

        # 確認必要的文字框皆存在
        if not all([
                spouse_col_lefttop_point,
                spouse_col_righttop_point,
                military_col_textBox,
                address_col_textBox, ]):
            return ""

        # 欄位的單位向量
        # 水平單位向量 = 配偶→役別
        col_i_arr = military_col_textBox.get_vertice_point("left_top")\
            - spouse_col_righttop_point
        # 垂直單位向量 = 住址→配偶
        col_j_arr = address_col_textBox.get_vertice_point("left_top")\
            - spouse_col_lefttop_point

        # 母親欄位的左下位置點: 設定為「役別」欄位名稱的右上邊
        mother_col_leftbottom_point = military_col_textBox.get_vertice_point(
            "right_top")
        # 母親欄位文字的區域
        mother_name_polygon = Polygon(
            [
                mother_col_leftbottom_point,
                mother_col_leftbottom_point - col_j_arr,
                mother_col_leftbottom_point - col_j_arr + col_i_arr*2,
                mother_col_leftbottom_point + col_i_arr*2,
            ]
        )
        # print("mother_name_polygon",  [
        #     mother_col_leftbottom_point,
        #     mother_col_leftbottom_point - col_j_arr,
        #     mother_col_leftbottom_point - col_j_arr + col_i_arr*2,
        #     mother_col_leftbottom_point + col_i_arr*2,
        # ])
        # 獲取母親名字
        mother_name = imageTextAnnotation.get_ocr_str_in_polygon(
            polygon=mother_name_polygon,
            i_arr=col_i_arr,
        )
        # 消除非中文字元
        mother_name = re.sub(r"[^\u4e00-\u9fa5]", "", mother_name)

        return mother_name

    @staticmethod
    def get_spouse_name_from_imageTextAnnotation(imageTextAnnotation:  "google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation") -> str:
        """ 獲取配偶名字

        Args:
            imageTextAnnotation (
                google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation)

        Returns:
            str
        """
        # 獲取 OCR 字串
        ocr_str = imageTextAnnotation.get_ocr_str()
        # 削去非中文字元 (但不消去換行字元)
        ocr_str = re.sub(r"[^\u4e00-\u9fa5\n]", "", ocr_str)

        # 策略1: 直接解析「配偶XXX役別XXX」的行文字
        for ocr_line_str in ocr_str.split("\n"):
            if ocr_line_str.startswith("配偶") and ("役別" in ocr_line_str):
                sqouse_name = ocr_line_str[2:ocr_line_str.index("役別")]
                if len(sqouse_name) >= 2:
                    return sqouse_name

        # 策略2: 建立錨點，偵測特定欄位文字位置
        # 獲取「役別」文字框
        military_col_textBox = imageTextAnnotation.get_textBox(
            startswith="役",
        )
        # 獲取「住址」文字框
        address_col_textBox = imageTextAnnotation.get_textBox(
            startswith="住",
        )
        # 先獲取「配偶」文字框: 根據「出生地」文字框位置來判斷 (因為「出生地」欄位的辨識度較高)
        birth_address_col_textBox = imageTextAnnotation.get_textBox(
            startswith="出生地",
        )
        spouse_col_righttop_point = None
        spouse_col_rightbottom_point = None
        if birth_address_col_textBox and address_col_textBox:
            up_shift_arr = birth_address_col_textBox.get_vertice_point(
                "left_top") - address_col_textBox.get_vertice_point("left_top")
            spouse_col_righttop_point = birth_address_col_textBox.get_vertice_point(
                "right_top") + up_shift_arr
            spouse_col_rightbottom_point = birth_address_col_textBox.get_vertice_point(
                "right_bottom") + up_shift_arr
        # 確認必要的文字框皆存在
        if not all([
                military_col_textBox,
                spouse_col_righttop_point,
                spouse_col_rightbottom_point, ]):
            return ""

        # 定義水平單位向量
        i_arr = birth_address_col_textBox.right_bottom - \
            birth_address_col_textBox.left_bottom

        # 定義配偶名字的區域
        spouse_name_polygon = Polygon(
            [
                spouse_col_righttop_point,
                military_col_textBox.get_vertice_point("left_top"),
                military_col_textBox.get_vertice_point("left_bottom"),
                spouse_col_rightbottom_point,
            ]
        )
        # print("spouse_name_polygon",  [
        #     spouse_col_righttop_point,
        #     military_col_textBox.get_vertice_point("left_top"),
        #     military_col_textBox.get_vertice_point("left_bottom"),
        #     spouse_col_rightbottom_point,
        # ])
        # 獲取配偶名字
        spouse_name = imageTextAnnotation.get_ocr_str_in_polygon(
            polygon=spouse_name_polygon,
            i_arr=i_arr,
        )
        # 消除非中文字元
        spouse_name = re.sub(r"[^\u4e00-\u9fa5]", "", spouse_name)

        return spouse_name

    @staticmethod
    def get_military_from_ocr_str(ocr_str: str) -> str:
        """ 獲取役別

        Args:
            ocr_str (str): 圖片文字

        Returns:
            str
        """
        # 替換常見誤判字
        ocr_str = ocr_str.replace("當", "常")

        for military_enum_str in MILITARY_ENUM_STR_SET:
            if military_enum_str in ocr_str:
                return military_enum_str
        return ""

    @staticmethod
    def get_birth_address_from_ocr_str(ocr_str: str) -> str:
        """ 獲取出生地

        Args:
            ocr_str (str): 圖片文字

        Returns:
            str
        """
        # 去掉「出生地」關鍵字
        ocr_str = ocr_str.replace("出生地", "")
        # 去掉非中文與數字的字元
        ocr_str = re.sub(r"[^\u4e00-\u9fa5\d\n]", "", ocr_str)
        # 遍歷行文字串列，返回符合格式的行文字串列
        for ocr_line_str in ocr_str.split("\n"):
            if len(ocr_line_str) == 6 and ocr_line_str[2] == "省":
                return ocr_line_str
            if len(ocr_line_str) == 3 and ocr_line_str[2] == "市":
                return ocr_line_str

        return ""

    @staticmethod
    def get_residence_address_from_ocr_str(ocr_str: str) -> str:
        """ 獲取居住地

        Args:
            ocr_str (str): 圖片文字

        Returns:
            str
        """
        # 去掉非中文與數字的字元
        ocr_str = re.sub(r"[^\u4e00-\u9fa5\d\n]", "", ocr_str)

        # 遍歷行文字串列，若發現符合格式的行文字串列，返回該行與下一行的合併文字
        ocr_line_str_list = []
        for ocr_line_str in ocr_str.split("\n"):
            # 去掉「住址」關鍵字
            while ocr_line_str.startswith("住") or ocr_line_str.startswith("址"):
                ocr_line_str = ocr_line_str[1:]
            ocr_line_str_list.append(ocr_line_str)

        # 獲取第一行地址
        residence_address_lineStr1 = ""
        for ocr_line_str in ocr_line_str_list:
            if len(ocr_line_str) > 6 and (ocr_line_str[2] == "縣" or ocr_line_str[2] == "市"):
                residence_address_lineStr1 = ocr_line_str
                ocr_line_str_list.remove(ocr_line_str)

        # 獲取第二行地址
        residence_address_lineStr2 = next(
            (
                ocr_line_str
                for ocr_line_str in ocr_line_str_list
                if sum(
                    kw in ocr_line_str
                    for kw in "路段街巷弄號之樓"
                ) >= 1
            ),
            ""
        )
        # 修正第二行地址: 若沒有「之、樓」字，則後面不該以數字結尾 (數字結尾視為誤判，故將其消除)
        while len(residence_address_lineStr2) and (
            not any([
                ("之" in residence_address_lineStr2),
                ("樓" in residence_address_lineStr2),
            ])
        ) and (residence_address_lineStr2[-1] in "0123456789"):
            residence_address_lineStr2 = residence_address_lineStr2[:-1]

        return residence_address_lineStr1 + residence_address_lineStr2

    @staticmethod
    def get_serial_code_from_imageTextAnnotation(imageTextAnnotation:  "google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation") -> str:
        """ 獲取身分證反面流水號

        Args:
            imageTextAnnotation (
                google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation)

        Returns:
            str
        """

        # 先獲取「配偶」文字框頂點位置點
        spouse_col_textBox = imageTextAnnotation.get_textBox(
            startswith="配",
        )
        # 獲取「役別」文字框頂點位置點
        military_col_textBox = imageTextAnnotation.get_textBox(
            startswith="役",
        )
        # 獲取「住址」文字框頂點位置點
        address_col_textBox = imageTextAnnotation.get_textBox(
            startswith="住",
        )

        # 若沒有文字框
        if not all([
                spouse_col_textBox,
                military_col_textBox,
                address_col_textBox, ]):
            ocr_str = imageTextAnnotation.get_ocr_str()
            # 設置匹配模式: 流水號格式 (獲取 ocr 文字中最後一個符合的格式)
            pattern = r"(?P<serial_code>(\d|[oOtI]){10})"
            match = None
            for match in re.finditer(pattern, ocr_str):
                pass
            if not match:
                return ""

            # 替換誤認的英文為數字
            return (
                match.group("serial_code")
                .replace("o", "0")
                .replace("O", "0")
                .replace("t", "0")
                .replace("I", "1")
                .replace("l", "1")
            )

        # 定義水平和垂直向量
        i_arr = military_col_textBox.left_top - spouse_col_textBox.right_top
        j_arr = address_col_textBox.left_top - spouse_col_textBox.left_top

        # 定義捕獲的區域
        serial_code_polygon = Polygon(
            [
                address_col_textBox.right_bottom,
                address_col_textBox.right_bottom + i_arr*3,
                address_col_textBox.right_bottom + i_arr*3 + j_arr*3,
                address_col_textBox.right_bottom + j_arr*3,

            ]
        )

        textBox_list = imageTextAnnotation.get_textBox_list(
            polygon=serial_code_polygon,
            # 不要去除重疊的文字框
            remove_stack_bool=False,
        )

        # 設置匹配模式: 流水號格式 (獲取 ocr 文字中最後一個符合的格式)
        for textBox in textBox_list:
            pattern = r"[\doOtI]{10}"
            for serial_code in re.findall(pattern, textBox.description):
                return (
                    serial_code
                    .replace("o", "0")
                    .replace("O", "0")
                    .replace("t", "0")
                    .replace("I", "1")
                    .replace("l", "1")
                )

        return ""
