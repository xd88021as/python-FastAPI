
from pydantic import BaseModel, Field

from libs import health_card, id_card, id_card_back
from libs.utils import StrictnessIntEnum
from .utils import (
    HasFaceBase,
)


class OcrValidation(BaseModel):
    id_card_verifyOut: id_card.VerifyOut = Field(
        ...,
        description="身分證正面 OCR 辨識結果",
    )
    id_card_back_verifyOut: id_card_back.VerifyOut = Field(
        ...,
        description="身分證背面 OCR 辨識結果",
    )
    health_card_verifyOut: health_card.VerifyOut = Field(
        ...,
        description="健保卡 OCR 辨識結果",
    )

    @classmethod
    def get_example(cls) -> "VerifyOut":
        return cls(
            id_card_verifyOut=id_card.VerifyOut.get_example(),
            id_card_back_verifyOut=id_card_back.VerifyOut.get_example(),
            health_card_verifyOut=health_card.VerifyOut.get_example(),
        )


class FaceValidation(BaseModel):
    id_card_faces_compare_score: float = Field(
        0.0,
        description="比對「身分證正面照: 證照人臉」和「持證自拍照: 證照人臉」的相似度 (0~100分)",
    )
    id_card_vs_person_face_compare_score: float = Field(
        0.0,
        description="比對「身分證正面照: 證照人臉」和「持證自拍照: 自拍人臉」的相似度 (0~100分)",
    )
    is_valid_bool: bool = Field(
        True,
        description="人臉辨識核實結果",
    )
    err_msg: str = Field(
        "",
        description="錯誤訊息",
    )
    STRICTNESS_INT: StrictnessIntEnum = Field(
        StrictnessIntEnum.MEDIUM,
        description="嚴謹度",
    )

    @classmethod
    def get_example(cls) -> "VerifyOut":
        return cls()


class VerifyOut(BaseModel):
    ocrValidation: OcrValidation = Field(
        ...,
        description="OCR 辨識與資料完整性核實結果",
    )
    infoValidation: id_card.Verification = Field(
        ...,
        description="資料一致性核實結果",
    )
    faceValidation: FaceValidation = Field(
        ...,
        description="人臉辨識核實結果",
    )
    is_valid_bool: bool = Field(
        True,
        description="身分驗證核實結果",
    )
    err_msg: str = Field(
        "",
        description="錯誤訊息",
    )

    @classmethod
    def get_example(cls) -> "VerifyOut":
        return cls(
            ocrValidation=OcrValidation.get_example(),
            infoValidation=id_card.Verification.get_example(),
            faceValidation=FaceValidation.get_example(),
        )


class HoldCardSelfie(HasFaceBase):
    pass
