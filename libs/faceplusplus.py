from typing import List
from typing_extensions import Literal
from fastapi import Body
import requests

from .utils import (
    BaseModel,
    Image,
    FaceBase,
    Config,
)


class Faceplusplus:
    """ Face++ API 實作
    """
    ENDPOINT = "https://api-us.faceplusplus.com/facepp/v3"
    API_KEY = Config.get().faceplusplus.api_key
    API_SECRET = Config.get().faceplusplus.api_secret

    class Face(FaceBase):
        """ Face++ 人臉
        """
        token: str
        gender: Literal["Male", "Female"] = None
        age: int = None

        class Config:
            fields = {
                "token": {"description": "人臉 token"},
                "gender": {"description": "性別"},
                "age": {"description": "年齡"},
            }

        @classmethod
        def get_face_list_from_image(
                cls,
                image: Image) -> List["Faceplusplus.Face"]:
            """ 自圖片建立 Facepp.Face 實例

            Args:
                image (Image): 圖片

            Raises:
                requests.exceptions.HTTPError: 網路連線問題

            Returns:
                List["Facepp.Face"]
            """
            # 解析圖片路徑為 base64
            img_base64str = image.get_base64str()

            # 送出請求: 辨識人臉 # Ref. https://console.faceplusplus.com/documents/5679127
            res = requests.post(
                url=f"{Faceplusplus.ENDPOINT}/detect",
                data=dict(
                    api_key=Faceplusplus.API_KEY,
                    api_secret=Faceplusplus.API_SECRET,
                    return_attributes="gender,age",
                    image_base64=img_base64str,
                )
            )
            res.raise_for_status()  # 若請求失敗則 raise 錯誤

            return [
                cls(
                    token=face["face_token"],
                    gender=face["attributes"]["gender"]["value"],
                    age=face["attributes"]["age"]["value"],
                )
                for face in res.json()["faces"]
            ]

        def compare_face(
                self,
                face: "Faceplusplus.Face",) -> float:
            """ 與另一個 Facepp.Face 之間的相似度

            Args:
                face (Facepp.Face): 另一個比較的臉

            Ref:
                https://console.faceplusplus.com/documents/5679308

            Raises:
                requests.exceptions.HTTPError: 網路連線問題

            Returns:
                float
            """

            assert isinstance(face, Faceplusplus.Face), "face 必須為 Facepp.Face"

            res = requests.post(
                url=f"{Faceplusplus.ENDPOINT}/compare",
                data=dict(
                    api_key=Faceplusplus.API_KEY,
                    api_secret=Faceplusplus.API_SECRET,
                    face_token1=self.token,
                    face_token2=face.token,
                )
            )
            res.raise_for_status()

            return res.json()["confidence"]


class ComapreOut(BaseModel):
    """ 臉部比對響應結果
    """
    score: float

    class Config:
        fields = {
            "score": {"description": "相似分數 (0~1)"},
        }
    
    @classmethod
    def get_post_example_body(cls)->Body:
        return Body(
            ...,
            examples={
                "臉部比對請求範例":{
                    "value": [
                        {
                            "token": "e0ca5ef32be4de002c90cd3b0187dcee",
                            "gender": "Male",
                            "age": 22
                        },
                        {
                            "token": "cb45f599cad1e88fe86b8eae0c51b713",
                            "gender": "Male",
                            "age": 27
                        }
                    ]
                }
            }
        )

    @classmethod
    def from_face_list(cls, face_list: List[Faceplusplus.Face]):
        """ 從 Facepp.Face 列表建立 ComapreOut 實例

        Args:
            face_list (List[Facepp.Face]): Facepp.Face 列表

        Raises:
            AssertionError: 輸入參數不符合格式
            HTTPError: 服務響應錯誤

        Returns:
            ComapreOut
        """
        assert isinstance(face_list, list), "face_list 必須為 Facepp.Face 列表"
        assert len(face_list) == 2, "face_list 必須為兩個 Facepp.Face"
        assert isinstance(
            face_list[0], Faceplusplus.Face), "face_list[0] 必須為 Facepp.Face"
        assert isinstance(
            face_list[1], Faceplusplus.Face), "face_list[1] 必須為 Facepp.Face"

        return cls(score=face_list[0].compare_face(face_list[1]))
