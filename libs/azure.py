from typing import List
import requests

from .utils import (
    BaseModel,
    Image,
    FaceBase,
    Config,
)


class Azure:
    """ Azure API 實作
    """
    ENDPOINT = Config.get().azure.endpoint
    SUBSCRIPTION_KEY = Config.get().azure.subscription_key

    class Face(FaceBase):
        """ Azure 人臉
        """
        token: str

        class Config:
            fields = {"token": {"description": "人臉 token"}}

        @classmethod
        def get_face_list_from_image(
            cls,
            image: Image
        ) -> List['Azure.Face']:
            """ 自圖片建立 Face 實例

            Args:
                image (Image): 圖片

            Raises:
                requests.exceptions.HTTPError: 網路連線問題

            Returns:
                List['Azure.Face']
            """

            # 送出請求: 辨識人臉 # Ref. https://docs.microsoft.com/zh-tw/rest/api/faceapi/face/detect-with-stream
            res = requests.post(
                url=f'{Azure.ENDPOINT}/face/v1.0/detect?overload=stream&returnFaceId=true&recognitionModel=recognition_04&returnRecognitionModel=true&detectionModel=detection_03',
                data=image.get_bytes(),
                headers={
                    'Ocp-Apim-Subscription-Key': Azure.SUBSCRIPTION_KEY,
                    'Content-Type': 'application/octet-stream',
                },
            )
            res.raise_for_status()  # 若請求失敗則 raise 錯誤

            return [
                cls(
                    token=face_dict['faceId'],
                )
                for face_dict in res.json()
            ]

        def compare_face(
            self,
            face: 'Azure.Face',
        ) -> float:
            """ 與另一個 Azure.Face 之間的相似度

            Args:
                face (Azure.Face): 另一個比較的臉

            Ref:
                https://learn.microsoft.com/en-us/rest/api/faceapi/face/verify-face-to-face?tabs=HTTP

            Raises:
                requests.exceptions.HTTPError: 網路連線問題

            Returns:
                float: 範圍: 0~100
            """

            assert isinstance(face, Azure.Face), "face 必須為 Azure.Face"

            res = requests.post(
                url=f'{Azure.ENDPOINT}/face/v1.0/verify',
                json=dict(
                    faceId1=self.token,
                    faceId2=face.token,
                ),
                headers={
                    'Ocp-Apim-Subscription-Key': Azure.SUBSCRIPTION_KEY,
                },
            )
            res.raise_for_status()
            return res.json()['confidence']*100


class ComapreOut(BaseModel):
    """ 臉部比對響應結果
    """
    score: float

    class Config:
        fields = {
            "score": {"description": "相似分數 (0~1)"},
        }

    # @classmethod
    # def get_post_example_body(cls) -> Body:
    #     return Body(
    #         ...,
    #         examples={
    #             "臉部比對請求範例": {
    #                 "value": [
    #                     {
    #                         "token": "e0ca5ef32be4de002c90cd3b0187dcee",
    #                         "gender": "Male",
    #                         "age": 22
    #                     },
    #                     {
    #                         "token": "cb45f599cad1e88fe86b8eae0c51b713",
    #                         "gender": "Male",
    #                         "age": 27
    #                     }
    #                 ]
    #             }
    #         }
    #     )

    @classmethod
    def from_face_list(cls, face_list: List[Azure.Face]):
        """ 從 Azure.Face 列表建立 ComapreOut 實例

        Args:
            face_list (List[Azure.Face]): Azure.Face 列表

        Raises:
            AssertionError: 輸入參數不符合格式
            HTTPError: 服務響應錯誤

        Returns:
            ComapreOut
        """
        assert isinstance(face_list, list), "face_list 必須為 Azure.Face 列表"
        assert len(face_list) == 2, "face_list 必須為兩個 Azure.Face"
        assert isinstance(
            face_list[0], Azure.Face), "face_list[0] 必須為 Azure.Face"
        assert isinstance(
            face_list[1], Azure.Face), "face_list[1] 必須為 Azure.Face"

        return cls(score=face_list[0].compare_face(face_list[1]))
