from typing import List

import requests

from .utils import (
    BaseModel,
    Config,
    FaceBase,
    Image,
)


class Face8:
    """ Face8 API 實作
    """
    ENDPOINT = "https://api.face8.ai/api"
    API_KEY = Config.get().face8.api_key
    API_SECRET = Config.get().face8.api_secret

    class Face(FaceBase):
        """ Face8 人臉
        """
        token: str
        liveness: float

        class Config:
            fields = {
                "token": {"description": "人臉 token"},
                "liveness": {"description": "活體指數 (0~1)"},
            }

        @classmethod
        def get_face_list_from_image(
                cls,
                image: Image) -> List['Face8.Face']:
            """ 自圖片建立 Face 實例串列

            Args:
                image (Image): 圖片

            Raises:
                requests.exceptions.HTTPError: 網路連線問題

            Returns:
                List['Face8.Face']
            """
            # 解析圖片路徑為 base64
            img_base64str = image.get_base64str()

            # 送出請求: 辨識人臉 # Ref.新版API(已找不到舊版): https://face8.ai/api-doc/#/
            res = requests.post(
                url=f'{Face8.ENDPOINT}/detect',
                data=dict(
                    api_key=Face8.API_KEY,
                    api_secret=Face8.API_SECRET,
                    return_attributes='liveness',
                    image_base64='data:image/jpeg;base64,' + img_base64str,
                )
            )
            res.raise_for_status()  # 若請求失敗則 raise 錯誤

            return [
                cls(
                    token=face_dict['face_token'],
                    liveness=face_dict['attributes']['liveness']['value'],
                )
                for face_dict in res.json()['faces']
            ]

        def compare_face(
                self,
                face: 'Face8.Face',) -> float:
            """ 與另一個 Face8.Face 之間的相似度

            Args:
                face (Face8.Face): 另一個比較的臉

            Raises:
                requests.exceptions.HTTPError: 網路連線問題

            Returns:
                float
            """

            assert isinstance(face, Face8.Face), "face 必須為 Face8.Face 類型"

            res = requests.post(
                url=f'{Face8.ENDPOINT}/compare',
                data=dict(
                    api_key=Face8.API_KEY,
                    api_secret=Face8.API_SECRET,
                    face_token1=self.token,
                    face_token2=face.token,
                )
            )
            res.raise_for_status()

            return res.json()['confidence']


class ComapreOut(BaseModel):
    """ 臉部比對響應結果
    """
    score: float

    class Config:
        fields = {
            "score": {"description": "相似分數 (0~1)"},
        }

    @classmethod
    def from_face_list(cls, face_list: List[Face8.Face]):
        """ 從 Facepp.Face 列表建立 ComapreOut 實例

        Args:
            face_list (List[Facepp.Face]): Facepp.Face 列表

        Raises:
            AssertionError: 輸入參數不符合格式
            HTTPError: 服務響應錯誤

        Returns:
            ComapreOut
        """
        # assert isinstance(face_list, list), "face_list 必須為 Facepp.Face 列表"
        # assert len(face_list) == 2, "face_list 必須為兩個 Facepp.Face"
        # assert isinstance(
        #     face_list[0], Face8.Face), "face_list[0] 必須為 Facepp.Face"
        # assert isinstance(
        #     face_list[1], Face8.Face), "face_list[1] 必須為 Facepp.Face"

        return cls(score=face_list[0].compare_face(face_list[1]))
