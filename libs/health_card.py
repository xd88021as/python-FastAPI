import datetime
import re
from typing import Tuple

import numpy as np
from pydantic import BaseModel, Field, constr, root_validator

from libs.id_card import Verification

from . import google_vison_ocr
from .google_vison_ocr import Point, Polygon
from .utils import (
    TAWIWAN_COMMON_SURNAME_LIST,
    InfoCardBase,
)

FIELDS = {
    "person_id": {"description": "身分證號碼"},
    "name": {"description": "姓名"},
    "birth_yyy": {"description": "生日日期(民國年)"},
    "birth_mm": {"description": "生日日期(月)"},
    "birth_dd": {"description": "生日日期(日)"},
    "code_str": {"description": "健保卡號碼"},
}


class Ocr(BaseModel):
    """ 身分證背面 OCR 辨識結果
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
    code_str: str | None = Field(
        None,
        description="健保卡號碼 (12碼)",
    )

    @classmethod
    def get_example(cls) -> "Ocr":
        return cls(
            person_id="A123456789",
            name="王小明",
            birth_yyy_int=80,
            birth_m_int=1,
            birth_d_int=1,
            code_str="000011112222",
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


class HealthCardOcrOut(BaseModel):
    """ 健保卡 ocr 辨識結果響應
    """
    person_id: str = ""
    name: str = ""
    birth_yyy: str = ""
    birth_mm: str = ""
    birth_dd: str = ""
    code_str: str = ""

    class Config:
        fields = FIELDS


class HealthCardStrict(HealthCardOcrOut):
    """ 健保卡嚴格資訊模型
    """
    person_id: str
    name: str
    birth_yyy: int
    birth_mm: int
    birth_dd: int
    code_str: constr(regex=r"^[0-9]{12}$")

    @root_validator
    def validate_birth_date(cls, values):
        """ 驗證生日日期
        """
        now_date = datetime.datetime.now().date()
        birth_date = datetime.date(
            values.get("birth_yyy")+1911,
            values.get("birth_mm"),
            values.get("birth_dd"),
        )
        assert (birth_date <= now_date), "出生日期應小於現在日期"
        return values


class HealthCard(InfoCardBase, HealthCardOcrOut):
    """ 健保卡
    """

    def get_strict(self) -> HealthCardStrict:
        """ 獲取身分證正面嚴格資訊模型

        Raises:
            ValidationError: 身分證正面資訊格式錯誤

        Returns:
            HealthCardStrict
        """
        return HealthCardStrict(**self.dict())

    @classmethod
    def from_imageTextAnnotation(
        cls,
        imageTextAnnotation: "google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation",
    ) -> "HealthCard":
        """ 根據 ocr 分析結果建立實例

        Args:
            imageTextAnnotation (ImageTextAnnotation): ocr 分析結果

        Returns:
            HealthCard
        """
        # 獲取 ocr 文字 # 去除空白字元
        ocr_str = imageTextAnnotation.get_ocr_str().replace(" ", "")
        # 獲取身分證號
        person_id = cls.get_person_id_from_ocr_str(imageTextAnnotation)
        # 獲取姓名 (可能會包含多餘的辨識文字在後面)
        name = cls.get_name_from_imageTextAnnotation(imageTextAnnotation)
        # 獲取生日日期
        birth_yyy, birth_mm, birth_dd = cls.get_birth_date_tuple_from_ocr_str(
            imageTextAnnotation
        )
        # 獲取健保卡號碼
        code_str = cls.get_code_str_from_ocr_str(ocr_str)

        return cls(
            person_id=person_id,
            name=name,
            birth_yyy=birth_yyy,
            birth_mm=birth_mm,
            birth_dd=birth_dd,
            code_str=code_str,
            ocr_str=ocr_str,
        )

    @staticmethod
    def get_person_id_from_ocr_str(imageTextAnnotation: 'google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation') -> str:
        """ 獲取身分證號

        Args:
            ocr_str (str): ocr 文字

        Returns:
            str: 身分證號
        """
        pattern = r"^[A-Z01]\d{9}$"
        for textBox in imageTextAnnotation.textAnnotations[1:]:
            person_id_str = textBox.description
            if not re.search(pattern, textBox.description):
                continue
            # 修正開頭英文字母被誤認為數字: 數字0 → 英文O / 數字1 → 英文I
            if person_id_str.startswith('0'):
                person_id_str = 'O' + person_id_str[1:]
            elif person_id_str.startswith('1'):
                person_id_str = 'I' + person_id_str[1:]
            return person_id_str
        return ""

    @staticmethod
    def get_name_from_ocr_str(ocr_str: str) -> str:
        """ 獲取姓名

        Args:
            ocr_str (str): ocr 文字

        Raises:
            RegexMatchException: 正規表示式不匹配

        Returns:
            str: 姓名
        """

        # 獲取標題「全民健康保險 NATIONALHEALTHINSURANCE」以下的字串
        while "ANCE" in ocr_str:
            ocr_str = "".join(ocr_str.split("ANCE")[1:])

        # 取代掉中文和換行以外的文字
        ocr_str = re.sub(r"[^\u4e00-\u9fa5\n]", "", ocr_str)
        # 獲取姓名候選字串串列，其中: 1.排除標題「全民健康保險」行文字 2.文字長度 2 以上
        _candidate_name_list = [
            line_str.strip()
            for line_str in ocr_str.split("\n")
            if ("全民健康" not in line_str) and (len(line_str.strip()) >= 2)
        ]

        # 贅字處理: 1.去除姓名左方的IC晶片被誤判為「日、月、目、匡、巨」的情況 2.去除空白的候選姓名
        candidate_name_list = []
        for candidate_name in _candidate_name_list:
            while next(iter(candidate_name), "") in [
                "日", "月", "目", "匡", "巨", "国", "四",
            ]:
                candidate_name = candidate_name[1:]
            if candidate_name:
                candidate_name_list.append(candidate_name)

        # 若無任何姓名候選字串串列，則返回空字串
        if not candidate_name_list:
            return ""

        # 根據台灣常見姓氏選出最可能為姓名的字串
        name = min(
            candidate_name_list,
            key=lambda candidate_name: (
                TAWIWAN_COMMON_SURNAME_LIST.index(candidate_name[0])
                if candidate_name[0] in TAWIWAN_COMMON_SURNAME_LIST
                else float("inf")
            )
        )

        return name

    @staticmethod
    def get_name_from_imageTextAnnotation(imageTextAnnotation: "google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation") -> str:
        """ 獲取姓名

        Args:
            imageTextAnnotation (
                google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation)

        Raises:
            RegexMatchException: 正規表示式不匹配

        Returns:
            str: 姓名
        """
        # 獲取以純 ocr 字串進行辨識得到的姓名
        from_ocr_str_name = HealthCard.get_name_from_ocr_str(
            imageTextAnnotation.get_ocr_str().replace(" ", "")
        )

        # 獲取健保卡左下角「0000」文字框
        textBox_list = imageTextAnnotation.textAnnotations[1:]
        a_0000_textBox = next(
            filter(
                lambda textBox: textBox.description == "0000",
                textBox_list
            ),
            None
        )
        if a_0000_textBox is None:
            return from_ocr_str_name

        # 獲取水平與垂直單位向量
        i_arr = (a_0000_textBox.right_top-a_0000_textBox.left_top)
        i_uarr: Point = i_arr / np.linalg.norm(i_arr.arr())
        j_arr = (a_0000_textBox.left_top-a_0000_textBox.left_bottom)
        j_uarr: Point = j_arr / np.linalg.norm(j_arr.arr())

        # 獲取姓名辨識範圍 (左上與右下座標點)
        name_area_lt = (
            a_0000_textBox.left_top
            + a_0000_textBox.w*(317/109)*i_uarr
            + a_0000_textBox.w*(552/109)*j_uarr
        )
        name_area_rb = (
            name_area_lt
            + a_0000_textBox.w*(815/109)*i_uarr
            - a_0000_textBox.w*(320/109)*j_uarr
        )

        # 獲取姓名辨識結果字串
        name_ocr_str = imageTextAnnotation.get_ocr_str_in_polygon(
            polygon=Polygon([
                [name_area_lt.x, name_area_lt.y],
                [name_area_rb.x, name_area_lt.y],
                [name_area_rb.x, name_area_rb.y],
                [name_area_lt.x, name_area_rb.y],
            ]),
            i_arr=i_arr,
        )
        # 取代掉非中文字和疫苗標籤關鍵字
        name_ocr_str = re.sub(r"[^\u4e00-\u9fa5\n]", "", name_ocr_str)
        name_ocr_str = (
            name_ocr_str if len(name_ocr_str) <= 3 else
            (
                name_ocr_str
                .replace("高端", "")
                .replace("追加", "")
                .replace("日期", "")
                .replace("期", "")
                .replace("甘", "")
                .replace("月", "")
            )
        )
        if len(name_ocr_str) != 3:
            return from_ocr_str_name
        return name_ocr_str

    @staticmethod
    def get_birth_date_tuple_from_ocr_str(imageTextAnnotation: 'google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation') -> Tuple[int, int, int]:
        """ 獲取生日日期

        Args:
            text (str): 輸入文字

        Raises:
            RegexMatchException: 正規表示式不匹配

        Returns:
            Tuple[str, str, str]: 生日日期
        """

        pattern = r"(?P<birth_yyy>\d+)/(?P<birth_mm>\d+)/(?P<birth_dd>\d+)"
        birth_date_str_list = [
            textBox.description
            for textBox in imageTextAnnotation.textAnnotations[1:]
            if re.search(pattern, textBox.description)
            # 排除因為標籤導致的誤判的生日年分
            if int(textBox.description.split('/')[0]) >= 24
        ]
        birth_date_str_list.sort(
            key=lambda birth_date_str: int(birth_date_str.split('/')[0])
        )

        if birth_date_str_list:
            return tuple(map(int, birth_date_str_list[0].split('/')))
        return "", "", ""

    @ staticmethod
    def get_code_str_from_ocr_str(ocr_str: str) -> str:
        """ 獲取健保卡號碼

        Args:
            text (str): 輸入文字

        Raises:
            RegexMatchException: 正規表示式不匹配

        Returns:
            str: 健保卡號碼
        """
        # 設置匹配模式: 健保卡號碼格式
        pattern = r"(?P<code_str>(\d|[oOtI]){12})"
        match = re.search(pattern, ocr_str)
        if not match:
            return ""

        # 替換誤認的英文為數字
        return (
            match.group("code_str")
            .replace("o", "0")
            .replace("O", "0")
            .replace("t", "0")
            .replace("I", "1")
            .replace("l", "1")
        )
