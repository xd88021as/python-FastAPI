import datetime
from typing import List, Tuple
from pydantic import ValidationError


from .utils import (
    BaseModel,
    Config,
    HasFaceBase,
    Image,
    logger,
)
from libs.faceplusplus import Faceplusplus
from libs.exceptions import IDCardValidationNotPassError, ServerError
from libs.id_card import IDCard, IDCardOcrOut, IDCardStrict
from libs.id_card_back import IDCardBack, IDCardBackOcrOut, IDCardBackStrict
from libs.health_card import HealthCard, HealthCardOcrOut, HealthCardStrict
from libs.hold_card_selfie import HoldCardSelfie


class FaceServerBase(BaseModel):
    """ 人臉辨識服務基底類
    """
    class FaceInfoBase(BaseModel):
        """ 人臉資訊基底類
        """
        face_count: int = 0
        is_face_count_valid: bool = False

        class Config:
            fields = {
                "face_list": {"description": "人臉列表."},
                "face_count": {"description": "人臉數量."},
                "is_face_count_valid": {"description": "人臉數量是否合法(身分證:1, 持證自拍:2)"},
            }

    class Config:
        fields = {
            "id_card": {"description": "身分證人臉資訊."},
            "hold_card_selfie": {"description": "持證自拍照人臉資訊."},
        }


class SelfieVerificationOut(BaseModel):
    """ 實名認證結果
    """

    class Ocr(BaseModel):
        """ 實名認證 OCR 辨識結果
        """
        id_card: IDCardOcrOut
        id_card_back: IDCardBackOcrOut
        health_card: HealthCardOcrOut

        @classmethod
        def from_images(
            cls,
            id_card_image: Image,
            id_card_back_image: Image,
            health_card_image: Image,
        ) -> Tuple["SelfieVerificationOut.Ocr", Tuple[IDCard, IDCardBack, HealthCard]]:
            """ 輸入三張照片, 回傳 Ocr, IDCard, IDCardBack, HealthCard

            Args:
                id_card_image: 身份證正面照片
                id_card_back_image: 身份證反面照片
                health_card_image: 健保卡照片

            Returns:
                SelfieVerificationOut.Ocr, (IDCard, IDCardBack, HealthCard)
            """

            id_card: IDCard = IDCard.from_image(id_card_image)
            id_card_back: IDCardBack = IDCardBack.from_image(
                id_card_back_image)
            health_card: HealthCard = HealthCard.from_image(health_card_image)
            logger.debug(f'{health_card = }')
            return cls(
                id_card=IDCardOcrOut(**id_card.dict()),
                id_card_back=IDCardBackOcrOut(**id_card_back.dict()),
                health_card=HealthCardOcrOut(**health_card.dict()),
            ), (id_card, id_card_back, health_card)

    class OcrValidation(BaseModel):
        """ 實名認證 OCR 辨識結果
        """

        class IDCardVerifyOut(BaseModel):

            class Verification(BaseModel):
                is_valid_bool: bool
                err_msg: str = None

            ocr: IDCardOcrOut
            verification: Verification

            @classmethod
            def from_id_card(
                cls,
                id_card: IDCard,
            ) -> Tuple["SelfieVerificationOut.OcrValidation.IDCardVerifyOut", Tuple[IDCardStrict]]:

                # 驗證身份證正面資料
                logger.debug("驗證身份證正面資料...")
                id_card_strict = None
                try:
                    id_card_strict = id_card.get_strict()
                except ValidationError as exc:
                    msg = f"身分證正面 OCR 資訊不完整. Detail: {exc!r}"
                    logger.warning(msg)
                # 驗證身分證合法性 (戶政 API)
                id_card_not_valid_msg = None
                # 若已開啟戶政 API 驗證功能
                if Config.get().household_registration_api.enabled:
                    # 若有完整身分證正面資料
                    if id_card_strict:
                        logger.debug("驗證身分證合法性 (戶政 API)...")
                        try:
                            id_card_strict.is_householdRegistration_valid()
                        # 若出現連線問題
                        except ServerError as exc:
                            id_card_not_valid_msg = f"戶政 API 連線發生問題. Detail: {exc!r}"
                            logger.warning(id_card_not_valid_msg)
                        # 若身分驗證未通過
                        except IDCardValidationNotPassError as exc:
                            id_card_not_valid_msg = f"戶政 API 驗證失敗. Detail: {exc!r}"
                            logger.warning(id_card_not_valid_msg)
                    # 若沒有完整身分證正面資料
                    else:
                        id_card_not_valid_msg = "身分證正面 OCR 資訊不完整."

                return cls(
                    ocr=IDCardOcrOut(**id_card.dict()),
                    verification=cls.Verification(
                        is_valid_bool=id_card_not_valid_msg is None,
                        err_msg=id_card_not_valid_msg
                    )
                ), (id_card_strict)

        class IDCardBackVerifyOut(BaseModel):

            class Verification(BaseModel):
                is_valid_bool: bool
                err_msg: str = None

            ocr: IDCardBackOcrOut
            verification: Verification

            @classmethod
            def from_id_card_back(
                cls,
                id_card_back: IDCardBack,
            ) -> Tuple["SelfieVerificationOut.OcrValidation.IDCardBackVerifyOut", Tuple[IDCardBackStrict]]:

                # 獲取身分證反面資料
                logger.debug("獲取身分證反面資料...")
                id_card_back_strict = None
                id_card_back_strict_msg = None
                try:
                    id_card_back_strict = id_card_back.get_strict()
                except ValidationError as exc:
                    id_card_back_strict_msg = f"身分證反面 OCR 資訊不完整. Detail: {exc!r}"
                    logger.warning(id_card_back_strict_msg)

                return cls(
                    ocr=IDCardBackOcrOut(**id_card_back.dict()),
                    verification=cls.Verification(
                        is_valid_bool=id_card_back_strict_msg is None,
                        err_msg=id_card_back_strict_msg
                    )
                ), (id_card_back_strict)

        class HealthCardVerifyOut(BaseModel):

            class Verification(BaseModel):
                is_valid_bool: bool
                err_msg: str = None

            ocr: HealthCardOcrOut
            verification: Verification

            @classmethod
            def from_health_card(
                cls,
                health_card: HealthCard,
            ) -> Tuple["SelfieVerificationOut.OcrValidation.HealthCardVerifyOut", Tuple[HealthCardStrict]]:

                # 獲取健保卡資料
                logger.debug("獲取健保卡資料...")
                health_card_strict = None
                health_card_strict_msg = None
                try:
                    health_card_strict = health_card.get_strict()
                except ValidationError as exc:
                    health_card_strict_msg = f"健保卡 OCR 資訊不完整. Detail: {exc!r}"
                    logger.warning(health_card_strict_msg)

                return cls(
                    ocr=HealthCardOcrOut(**health_card.dict()),
                    verification=cls.Verification(
                        is_valid_bool=health_card_strict_msg is None,
                        err_msg=health_card_strict_msg
                    )
                ), (health_card_strict)

        id_card_verify_out: IDCardVerifyOut
        id_card_back_verify_out: IDCardBackVerifyOut
        health_card_verify_out: HealthCardVerifyOut

        @classmethod
        def from_ocr_objs(
            cls,
            id_card: IDCard,
            id_card_back: IDCardBack,
            health_card: HealthCard,
        ) -> Tuple["SelfieVerificationOut.OcrValidation", Tuple[IDCardStrict]]:

            id_card_verify_out, (id_card_strict) = cls.IDCardVerifyOut.from_id_card(
                id_card=id_card)
            id_card_back_verify_out, (id_card_back_strict) = cls.IDCardBackVerifyOut.from_id_card_back(
                id_card_back=id_card_back)
            health_card_verify_out, (health_card_strict) = cls.HealthCardVerifyOut.from_health_card(
                health_card=health_card)

            return cls(
                id_card_verify_out=id_card_verify_out,
                id_card_back_verify_out=id_card_back_verify_out,
                health_card_verify_out=health_card_verify_out,
            ), (id_card_strict, id_card_back_strict, health_card_strict)

    class InfoValidation(BaseModel):
        """ 實名認證資料驗證結果
        """
        is_valid_bool: bool
        err_msg: str = None

        class Config:
            fields = {
                "is_match": {"description": "個人資料是否相符 (比對身分證正面和健保卡資訊)."},
                "msg": {"description": "個人資料不相符錯誤訊息 (比對身分證正面和健保卡資訊)."},
            }

        @classmethod
        def from_ocr_strict_objs(
            cls,
            id_card_strict: IDCardStrict,
            health_card_strict: HealthCardStrict,
        ) -> "SelfieVerificationOut.InfoValidation":

            # 判斷個人資料是否相符 (比對身分證正面和健保卡資訊)
            is_not_match_msg = None  # 預設沒有錯誤訊息
            # 若身分證正面與健保卡皆有完整的資料
            if all([id_card_strict, health_card_strict]):
                for k, v in health_card_strict.dict().items():
                    if (k in id_card_strict.dict()) and (v != id_card_strict.dict()[k]):
                        is_not_match_msg = f"身分證與健保卡個人資料不相符. ({k}: {v} != {id_card_strict.dict()[k]})"
                        break
            # 若身分證正面或健保卡沒有完整的資料
            else:
                is_not_match_msg = "身分證或健保卡個人資料不完全."

            return cls(
                is_valid_bool=(is_not_match_msg is None),
                err_msg=is_not_match_msg,
            )

    class FaceDetect(BaseModel):
        """ 各服務辨識各證件人臉列表結果
        """
        class FaceplusplusFaceServer(FaceServerBase):
            class FaceInfo(FaceServerBase.FaceInfoBase):
                face_list: List[Faceplusplus.Face] = []
            id_card: FaceInfo
            hold_card_selfie: FaceInfo

        faceplusplus: FaceplusplusFaceServer

        class Config:
            fields = {
                "faceplusplus": {"description": "Face++ 服務辨識各證件人臉列表結果."},
            }

        @classmethod
        def from_images(
                cls,
                id_card: HasFaceBase,
                hold_card_selfie: HasFaceBase,
        ) -> "SelfieVerificationOut.FaceDetect":
            # 確認參數類型正確
            assert isinstance(id_card, HasFaceBase)
            assert isinstance(hold_card_selfie, HasFaceBase)

            # 建立實例字典
            faceValidation_dict = dict()
            for server_name in ["Faceplusplus"]:
                logger.debug(f"建立 {server_name} 服務辨識各證件人臉列表結果...")
                server_dict = dict()
                for document, document_name, valid_face_count in zip(
                    [id_card, hold_card_selfie],
                    ["id_card", "hold_card_selfie"],
                    (1, 2)
                ):
                    face_list = document.get_face_list(server_name)
                    face_count = len(face_list)
                    is_face_count_valid = (face_count == valid_face_count)
                    server_dict[document_name] = dict(
                        face_list=face_list,
                        face_count=face_count,
                        is_face_count_valid=is_face_count_valid,
                    )

                faceValidation_dict[server_name.lower()] = server_dict
            return cls.parse_obj(faceValidation_dict)

    class FaceComparison(BaseModel):
        """ 各服務辨識各證件人臉比對結果
        """
        class FaceplusplusServer(BaseModel):

            class IDCardFacesCompare(BaseModel):
                """ 比對「身分證正面照: 證照人臉」和「持證自拍照: 證照人臉」的結果
                """
                score: float = 0.0
                is_valid: bool = False
                msg: str = None

                class Config:
                    fields = {
                        "score": {"description": "相似度分數 (face++: 0~100)."},
                        "msg": {"description": "錯誤訊息."},
                        "is_valid": {
                            "description": (
                                "是否通過門檻值.\n\n"
                                "face++: 相似度應達70%上"
                            )
                        },
                    }

            class IDCardVsPersonFacesCompare(BaseModel):
                """ 比對「身分證正面照: 證照人臉」和「持證自拍照: 自拍人臉」的結果
                """
                score: float = 0.0
                is_valid: bool = False
                msg: str = None

                class Config:
                    fields = {
                        "score": {"description": "相似度分數 (face++: 0~100)."},
                        "msg": {"description": "錯誤訊息."},
                        "is_valid": {
                            "description": (
                                "是否通過門檻值.\n\n"
                                "face++:\n\n"
                                " - 若發證不滿 2 年，則相似度應達 70 分以上\n"
                                " - 若發證不滿 5 年，則相似度應達 65 分以上\n"
                                " - 若發證 5 年以上，則相似度應達 60 分以上\n"
                            )
                        },
                    }

            id_card_faces_compare: IDCardFacesCompare
            id_card_vs_person_faces_compare: IDCardVsPersonFacesCompare

            @classmethod
            def from_faceDetect(
                cls,
                faceDetect: "SelfieVerificationOut.FaceDetect",
                idCard: IDCard,
            ) -> "SelfieVerificationOut.FaceComparison.FaceplusplusServer":
                logger.debug("進行 Face++ 人臉比對...")

                # 獲取 Face++ 服務的人臉辨識結果 (身分證正面、持證自拍照)
                faceplusplus_id_card_face_list = faceDetect.faceplusplus.id_card.face_list
                faceplusplus_hold_card_selfie_face_list = faceDetect.faceplusplus.hold_card_selfie.face_list

                # 確認人臉數量正確
                if (
                    len(faceplusplus_id_card_face_list) != 1 or
                    len(faceplusplus_hold_card_selfie_face_list) != 2
                ):
                    return cls(
                        id_card_faces_compare=cls.IDCardFacesCompare(
                            score=0.0,
                            is_valid=False,
                            msg="身分證正面人臉數量不為 1 個，或持證自拍照人臉數量不為 2 個."
                        ),
                        id_card_vs_person_faces_compare=cls.IDCardVsPersonFacesCompare(
                            score=0.0,
                            is_valid=False,
                            msg="身分證正面人臉數量不為 1 個，或持證自拍照人臉數量不為 2 個."
                        )
                    )

                # Face++ 服務的人臉比對結果
                faceplusplus_id_card_face = faceplusplus_id_card_face_list[0]

                # 獲取人臉比對相似度分數
                (
                    # 獲取「身分證正面照: 證照人臉」和「持證自拍照: 證照人臉」相似度分數
                    id_card_faces_compare_score,
                    # 獲取「身分證正面照: 證照人臉」和「持證自拍照: 自拍人臉」相似度分數
                    id_card_vs_person_faces_compare_score,
                ) = sorted([
                    faceplusplus_id_card_face.compare_face(face)
                    for face in faceplusplus_hold_card_selfie_face_list
                ], reverse=True)
                logger.debug(f"{id_card_faces_compare_score = }")
                logger.debug(f"{id_card_vs_person_faces_compare_score = }")

                # 比對「持證自拍照:證照人臉」和「身分證正面照:證照人臉」相似度應達80%上
                id_card_faces_compare_msg = None
                if id_card_faces_compare_score < 80:
                    id_card_faces_compare_msg = "「持證自拍照:證照人臉」和「身分證正面照:證照人臉」相似度應達 80% 以上"

                # 比對「持證自拍照:自拍人臉」和「身分證正面照:證照人臉」相似度，符合以下條件:
                # 若發證不滿 2 年，則相似度應達 70 分以上
                id_card_vs_person_faces_compare_msg = None
                # 若身分證 ocr 可獲取出生年份，則計算發證至今年已過幾年
                if idCard.apply_yyy != "":
                    # 獲取發證西元年分
                    idCard_apply_yyyy_int = int(idCard.apply_yyy) + 1911
                    # 獲取今年西元年分
                    now_yyyy_int = datetime.datetime.now().year
                    # 計算發證至今年已過幾年
                    idCard_apply_passed_year_int = now_yyyy_int - idCard_apply_yyyy_int

                    if (
                        idCard_apply_passed_year_int < 2 and
                        id_card_vs_person_faces_compare_score < 70
                    ):
                        id_card_vs_person_faces_compare_msg = f"「持證自拍照:自拍人臉」和「身分證正面照:證照人臉」相似度應達 80% 以上 (發證經過年數:{idCard_apply_passed_year_int})"
                    # 若發證不滿 5 年，則相似度應達 65 分以上
                    if (
                        idCard_apply_passed_year_int < 5 and
                        id_card_vs_person_faces_compare_score < 65
                    ):
                        id_card_vs_person_faces_compare_msg = f"「持證自拍照:自拍人臉」和「身分證正面照:證照人臉」相似度應達 65% 以上 (發證經過年數:{idCard_apply_passed_year_int})"
                    # 若發證 5 年以上，則相似度應達 60 分以上
                    if id_card_vs_person_faces_compare_score < 60:
                        id_card_vs_person_faces_compare_msg = f"「持證自拍照:自拍人臉」和「身分證正面照:證照人臉」相似度應達 60% 以上 (發證經過年數:{idCard_apply_passed_year_int})"

                # 若身分證 ocr 不可獲取出生年份
                else:
                    id_card_vs_person_faces_compare_msg = "身分證 ocr 無法獲取出生年份，故缺少標準檢驗「持證自拍照:自拍人臉」和「身分證正面照:證照人臉」相似度"

                return cls(
                    id_card_faces_compare=cls.IDCardFacesCompare(
                        score=id_card_faces_compare_score,
                        is_valid=(id_card_faces_compare_msg is None),
                        msg=id_card_faces_compare_msg,
                    ),
                    id_card_vs_person_faces_compare=cls.IDCardVsPersonFacesCompare(
                        score=id_card_vs_person_faces_compare_score,
                        is_valid=(
                            id_card_vs_person_faces_compare_msg is None),
                        msg=id_card_vs_person_faces_compare_msg,
                    )
                )

        faceplusplus: FaceplusplusServer

        class Config:
            fields = {
                "id_card_faces_compare_score": {"description": "辨識各證件人臉列表結果."},
                "id_card_vs_person_face_compare_score": {"description": "辨識各證件人臉列表結果."},
                "is_valid_bool": {"description": "辨識各證件人臉列表結果."},
                "err_msg": {"description": "辨識各證件人臉列表結果不相符錯誤訊息."},
                "STRICTNESS_INT": {"description": "嚴謹度 1: LOW, 2: MEDIUM, 3: HIGH"},
            }

        @classmethod
        def from_faceDetect(
            cls,
            faceDetect: "SelfieVerificationOut.FaceDetect",
            idCard: IDCard,
        ) -> "SelfieVerificationOut.FaceComparison":
            return cls(
                faceplusplus=cls.FaceplusplusServer.from_faceDetect(
                    faceDetect=faceDetect,
                    idCard=idCard,
                ),
            )

    class FaceValidation(BaseModel):

        id_card_faces_compare_score: float = 0.0
        id_card_vs_person_face_compare_score: float = 0.0
        is_valid_bool: bool = True
        err_msg: str = None
        STRICTNESS_INT: int = 2

        @classmethod
        def from_faceComparison(
            cls,
            faceDetect: "SelfieVerificationOut.FaceDetect",
            faceComparison: "SelfieVerificationOut.FaceComparison",
            strictness_int: int,
        ) -> "SelfieVerificationOut.FaceValidation":
            logger.debug("驗證各服務比對結果...")

            is_face_detect = (faceDetect.faceplusplus.id_card.is_face_count_valid and
                              faceDetect.faceplusplus.hold_card_selfie.is_face_count_valid)
            is_id_card_faces_compare = faceComparison.faceplusplus.id_card_faces_compare.is_valid
            is_id_card_vs_person_faces_compare = faceComparison.faceplusplus.id_card_vs_person_faces_compare.is_valid

            if not is_face_detect:
                err_msg = "辨識各證件人臉列表結果不相符"
            elif not is_id_card_faces_compare:
                err_msg = "身分證正面人臉與持證自拍照證件臉比對相似度分數不符合門檻"
            elif not is_id_card_vs_person_faces_compare:
                err_msg = "身分證正面人臉與持證自拍照人臉比對相似度分數不符合門檻"
            else:
                err_msg = None

            return cls(
                id_card_faces_compare_score=faceComparison.faceplusplus.id_card_faces_compare.score,
                id_card_vs_person_face_compare_score=faceComparison.faceplusplus.id_card_vs_person_faces_compare.score,
                is_valid_bool=err_msg is None,
                err_msg=err_msg,
                STRICTNESS_INT=strictness_int,
            )

    ocr_validation: OcrValidation
    info_validation: InfoValidation
    face_validation: FaceValidation
    is_valid_bool: bool
    err_msg: str = None

    @classmethod
    def from_image_bytes(
        cls,
        id_card_image_bytes: bytes,
        id_card_back_image_bytes: bytes,
        health_card_image_bytes: bytes,
        hold_card_selfie_image_bytes: bytes,
        strictness_int: int
    ) -> "SelfieVerificationOut":
        """ 將身分證正面照、身分證背面照、健保卡正面照、持證自拍照，進行身分證驗證

        Args:
            id_card_image_bytes (bytes): 身分證正面照
            id_card_back_image_bytes (bytes): 身分證背面照
            health_card_image_bytes (bytes): 健保卡正面照
            hold_card_selfie_image_bytes (bytes): 持證自拍照

        Returns:
            SelfieVerificationOut
        """

        # 獲已處理照片實例: 1.身分證正面 2.身分證反面 3.健保卡 4.持身分證自拍照
        logger.debug("正在處理四張照片...")
        (
            id_card_image,
            id_card_back_image,
            health_card_image,
            hold_card_selfie_image,
        ) = (
            Image(bytes_=id_card_image_bytes),
            Image(bytes_=id_card_back_image_bytes),
            Image(bytes_=health_card_image_bytes),
            Image(bytes_=hold_card_selfie_image_bytes),
        )

        # 獲取各證件 ocr 辨識結果
        ocr, (id_card, id_card_back, health_card) = SelfieVerificationOut.Ocr.from_images(
            id_card_image=id_card_image,
            id_card_back_image=id_card_back_image,
            health_card_image=health_card_image,
        )

        ocrValidation, (id_card_strict, id_card_back_strict, health_card_strict) = SelfieVerificationOut.OcrValidation.from_ocr_objs(
            id_card=id_card,
            id_card_back=id_card_back,
            health_card=health_card,
        )

        infoValidation = SelfieVerificationOut.InfoValidation.from_ocr_strict_objs(
            id_card_strict=id_card_strict,
            health_card_strict=health_card_strict,
        )

        faceDetect = SelfieVerificationOut.FaceDetect.from_images(
            id_card=id_card,
            hold_card_selfie=HoldCardSelfie(image=hold_card_selfie_image),
        )

        faceComparison = SelfieVerificationOut.FaceComparison.from_faceDetect(
            faceDetect=faceDetect,
            idCard=id_card,
        )

        faceValidation = SelfieVerificationOut.FaceValidation.from_faceComparison(
            faceDetect=faceDetect,
            faceComparison=faceComparison,
            strictness_int=strictness_int,
        )

        err_msg = (
            ocrValidation.id_card_verify_out.verification.err_msg
            or ocrValidation.id_card_back_verify_out.verification.err_msg
            or ocrValidation.health_card_verify_out.verification.err_msg
            or infoValidation.err_msg
            or faceValidation.err_msg
            or None
        )

        logger.debug("selfie verification complete.")
        return cls(
            ocr_validation=ocrValidation,
            info_validation=infoValidation,
            face_validation=faceValidation,
            is_valid_bool=err_msg is None,
            err_msg=err_msg,
        )
