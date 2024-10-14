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
    ocr: Ocr
    verification: Verification

    @classmethod
    def get_example(cls) -> "VerifyOut":
        return cls(
            ocr=Ocr.get_example(),
            verification=Verification.get_example(),
        )


class HealthCardOcrOut(BaseModel):
    person_id: str = ""
    name: str = ""
    birth_yyy: str = ""
    birth_mm: str = ""
    birth_dd: str = ""
    code_str: str = ""

    class Config:
        fields = FIELDS


class HealthCardStrict(HealthCardOcrOut):
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
    def get_strict(self) -> HealthCardStrict:
        return HealthCardStrict(**self.dict())

    @classmethod
    def from_imageTextAnnotation(
        cls,
        imageTextAnnotation: "google_vison_ocr.GoogleVisonOCR.ImageTextAnnotation",
    ) -> "HealthCard":
        ocr_str = imageTextAnnotation.get_ocr_str().replace(" ", "")
        person_id = cls.get_person_id_from_ocr_str(imageTextAnnotation)
        name = cls.get_name_from_imageTextAnnotation(imageTextAnnotation)
        birth_yyy, birth_mm, birth_dd = cls.get_birth_date_tuple_from_ocr_str(
            imageTextAnnotation
        )
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
        pattern = r"^[A-Z01]\d{9}$"
        for textBox in imageTextAnnotation.textAnnotations[1:]:
            person_id_str = textBox.description
            if not re.search(pattern, textBox.description):
                continue
            if person_id_str.startswith('0'):
                person_id_str = 'O' + person_id_str[1:]
            elif person_id_str.startswith('1'):
                person_id_str = 'I' + person_id_str[1:]
            return person_id_str
        return ""

    @staticmethod
    def get_name_from_ocr_str(ocr_str: str) -> str:
        while "ANCE" in ocr_str:
            ocr_str = "".join(ocr_str.split("ANCE")[1:])

        ocr_str = re.sub(r"[^\u4e00-\u9fa5\n]", "", ocr_str)
        _candidate_name_list = [
            line_str.strip()
            for line_str in ocr_str.split("\n")
            if ("全民健康" not in line_str) and (len(line_str.strip()) >= 2)
        ]

        candidate_name_list = []
        for candidate_name in _candidate_name_list:
            while next(iter(candidate_name), "") in [
                "日", "月", "目", "匡", "巨", "国", "四",
            ]:
                candidate_name = candidate_name[1:]
            if candidate_name:
                candidate_name_list.append(candidate_name)

        if not candidate_name_list:
            return ""

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
        from_ocr_str_name = HealthCard.get_name_from_ocr_str(
            imageTextAnnotation.get_ocr_str().replace(" ", "")
        )

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

        i_arr = (a_0000_textBox.right_top-a_0000_textBox.left_top)
        i_uarr: Point = i_arr / np.linalg.norm(i_arr.arr())
        j_arr = (a_0000_textBox.left_top-a_0000_textBox.left_bottom)
        j_uarr: Point = j_arr / np.linalg.norm(j_arr.arr())

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

        name_ocr_str = imageTextAnnotation.get_ocr_str_in_polygon(
            polygon=Polygon([
                [name_area_lt.x, name_area_lt.y],
                [name_area_rb.x, name_area_lt.y],
                [name_area_rb.x, name_area_rb.y],
                [name_area_lt.x, name_area_rb.y],
            ]),
            i_arr=i_arr,
        )
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
