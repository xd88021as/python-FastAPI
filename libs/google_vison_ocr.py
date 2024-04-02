from pathlib import Path
from typing import Callable, List, Optional
from typing_extensions import Literal, Self
from anyio import Any
import numpy as np
import requests
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import matplotlib as mpl
from shapely.geometry import Polygon
from shapely.geometry import Point as ShapelyPoint

from .utils import (
    Config,
    BaseModel,
)


def zh_fp(fontsize: float):
    """ 設置中文字型
    """
    font_path = Path(__file__).parent.parent / "font"
    return mpl.font_manager.FontProperties(
        fname=str(font_path / "msjhbd.ttc"),
        weight=1000,
        style="normal",
        size=fontsize,
    )


class Point(ShapelyPoint):
    """ 定義 Point 物件 (位置向量)

    2022/04/26 13:42:01 docs:📝edit type hint

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"({self.x}, {self.y})"

    def __repr__(self):
        return f"Point({self.x}, {self.y})"

    def arr(self):
        return np.array([self.x, self.y])

    def __sub__(self, other: Self) -> Self:
        """ 相減時可得到位移向量

        Args:
            other (Point): [description]

        Returns:
            Point
        """
        return Point(self.x - other.x, self.y - other.y)

    def __add__(self, other: Self) -> Self:
        """ 相加時可得到新的位置向量

        Args:
            other (Point): [description]

        Returns:
            Point
        """
        return Point(self.x + other.x, self.y + other.y)

    def __mul__(self, scale: float) -> Self:
        """ 乘上數字時可得到伸縮的位移向量

        Args:
            scale (float): 向量係數

        Returns:
            Point
        """
        return Point(self.x * scale, self.y * scale)

    def __rmul__(self, scale: float) -> Self:
        return self * scale

    def __truediv__(self, scale: float) -> Self:
        return self * (1 / scale)


class GoogleVisonOCR:
    """ Google Vision OCR API 實作

    log:
        2022/09/27 16:24:06 fix: 🐛修正 TextBox.h、TextBox.w 可能給出負值的問題
        2022/03/24 13:37:30 feat: ✨add get_textBox_list_by_str_filter()
        2022/03/22 16:49:47 feat: ✨add get_correction_degree()

    Ref:
        API 文件: https://cloud.google.com/vision/docs/ocr
    """
    API_KEY = Config.get().google_vison_ocr.api_key
    URL = "https://vision.googleapis.com/v1/images:annotate?alt=json&key=" + API_KEY
    REQUEST_IMGS_MAX_INT = 16

    class TextBoxVertice(BaseModel):
        """ 文字框多邊形頂點位置
        """
        x: int = 0
        y: int = 0

    class TextBoxPoly(BaseModel):
        """ 文字框多邊形
        """
        vertices: List["GoogleVisonOCR.TextBoxVertice"]

        def poly_collection(self) -> PolyCollection:
            """ 獲取 matplotlib.collections.PolyCollection
            """
            return PolyCollection([
                [
                    [
                        vertice.x,
                        vertice.y
                    ]
                    for vertice in self.vertices
                ]],
                edgecolors="red",
                facecolors="none",
                linewidths=1,
            )

    class TextBox(BaseModel):
        """ 文字框
        """
        description: str
        boundingPoly: "GoogleVisonOCR.TextBoxPoly"
        center_point: Optional[Any] = None

        class Config:
            fields = {"description": {"description": "文字內容"}}

        def plot(self, ax: plt.Axes) -> None:
            """ 繪製 TextBox
            """
            # 繪製文字框
            ax.add_collection(
                self.boundingPoly.poly_collection(),
            )
            # 繪製文字
            plt.text(
                self.boundingPoly.vertices[0].x,
                self.boundingPoly.vertices[0].y,
                self.description,
                color="red",
                fontproperties=zh_fp(12),
            )

        @property
        def area(self):
            """ 獲取面積

            Returns:
                float: 面積
            """
            return self.get_polygon().area

        def get_center_point(self) -> Point:
            """ 獲取平均中心點
            """
            if self.center_point is None:
                self.center_point = Point(
                    sum(
                        vertice.x
                        for vertice in self.boundingPoly.vertices
                    ) / len(self.boundingPoly.vertices),
                    sum(
                        vertice.y
                        for vertice in self.boundingPoly.vertices
                    ) / len(self.boundingPoly.vertices),
                )

            return self.center_point

        def get_vertice_point(
                self,
                position: Literal[
                    "left_top",
                    "left_bottom",
                    "right_top",
                    "right_bottom",
                ],) -> Point:
            """ 獲取文字框頂點

            Args:
                position (Literal["left_top", "left_bottom", "right_top", "right_bottom"]): 頂點位置

            Returns:
                Point
            """
            # 文字框頂點與序號對照串列
            position_mapping_index_list = [
                "left_top",
                "right_top",
                "right_bottom",
                "left_bottom",
            ]

            position_index = position_mapping_index_list\
                .index(position)
            return Point(
                self.boundingPoly.vertices[position_index].x,
                self.boundingPoly.vertices[position_index].y,
            )

        @property
        def left_top(self) -> Point:
            """ 獲取左上頂點

            Returns:
                Point
            """
            return self.get_vertice_point("left_top")

        @property
        def left_bottom(self) -> Point:
            """ 獲取左下頂點

            Returns:
                Point
            """
            return self.get_vertice_point("left_bottom")

        @property
        def right_top(self) -> Point:
            """ 獲取右上頂點

            Returns:
                Point
            """
            return self.get_vertice_point("right_top")

        @property
        def right_bottom(self) -> Point:
            """ 獲取右下頂點

            Returns:
                Point
            """
            return self.get_vertice_point("right_bottom")

        @property
        def center(self) -> Point:
            """ 獲取中心點

            Returns:
                Point
            """
            return self.get_center_point()

        @property
        def h(self) -> int:
            """ 獲取高度

            Returns:
                float: 高度
            """
            return int(
                np.linalg.norm(self.right_bottom - self.right_top)
            )

        @property
        def w(self) -> int:
            """ 獲取寬度

            Returns:
                float: 寬度
            """
            return int(
                np.linalg.norm(self.right_bottom - self.left_bottom)
            )

        def get_polygon(self) -> Polygon:
            """ 獲取多邊形

            Returns:
                Polygon: 多邊形
            """
            return Polygon(
                [
                    [
                        vertice.x,
                        vertice.y
                    ]
                    for vertice in self.boundingPoly.vertices
                ]
            )

        def crawl(
            self,
            direction_chr: Literal["r", "l"],
            textBox_list: List[Self],
        ) -> Optional[Self]:
            """ 獲取鄰近的文字框

            Args:
                direction_chr (Literal["r", "l"]): 爬取方向
                textBox_list (List["GoogleVisonOCR.TextBox"]): 文字框列表

            Returns:
                Optional["GoogleVisonOCR.TextBox"]: 鄰近文字框
            """

            # 建立偵測區域多邊形: 以文字框的右上或左上角為中心的小方塊範圍
            detect_square_len = self.h
            detect_center_point = (
                self.right_top if direction_chr == "r" else
                self.left_top
            )
            detect_polygon = Polygon([
                [
                    detect_center_point.x - detect_square_len*0.7,
                    detect_center_point.y - detect_square_len/2,
                ],
                [
                    detect_center_point.x + detect_square_len/2,
                    detect_center_point.y - detect_square_len/2,
                ],
                [
                    detect_center_point.x + detect_square_len*0.7,
                    detect_center_point.y + detect_square_len/2,
                ],
                [
                    detect_center_point.x - detect_square_len/2,
                    detect_center_point.y + detect_square_len/2,
                ]
            ])

            # 捕捉鄰近文字框串列: 左上角或右上角落在偵測範圍的其她文字框
            near_textBox_list = [
                textBox
                for textBox in textBox_list
                if detect_polygon.contains(
                    textBox.left_top if direction_chr == "r" else
                    textBox.right_top
                )
                if textBox.center != self.center
            ]
            # 捕捉最靠右或最靠左的文字框
            near_textBox = (
                min if direction_chr == "r" else
                max
            )(
                near_textBox_list,
                key=lambda textBox: textBox.center.x,
                default=None
            )

            return near_textBox

        def get_expanded_lineBox(
            self,
            textBox_list: List[Self],
        ) -> "LineBox":
            """ 延伸文字框到行框

            Args:
                textBox_list (List["GoogleVisonOCR.TextBox"]): 文字框列表

            Returns:
                "LineBox": 行框
            """
            # 找出文字框的鄰近文字框
            right_textBox_list = []
            left_textBox_list = []
            right_textBox = self.crawl("r", textBox_list)
            while right_textBox is not None:
                right_textBox_list.append(right_textBox)
                textBox_list.remove(right_textBox)
                right_textBox = right_textBox.crawl("r", textBox_list)
            left_textBox = self.crawl("l", textBox_list)
            while left_textBox is not None:
                left_textBox_list.append(left_textBox)
                textBox_list.remove(left_textBox)
                left_textBox = left_textBox.crawl("l", textBox_list)
            return LineBox(
                textBox_list=[self] + left_textBox_list + right_textBox_list,
            )

    class ImageTextAnnotation(BaseModel):
        """ 圖片文字框分析結果
        """
        textAnnotations: List["GoogleVisonOCR.TextBox"] = []
        lineBox_list_: Any = None

        def plot(self, ax: plt.Axes, obj_str: str = "textBox") -> None:
            """ 繪製 TextBox
            """
            if obj_str == "textBox":
                for textBox in self.textAnnotations:
                    textBox.plot(ax)
            elif obj_str == "lineBox":
                for lineBox in self.get_lineBox_list():
                    lineBox.plot(ax)

        def get_textBox_list(
                self,
                polygon: Polygon = None,
                remove_stack_bool: bool = True) -> List["GoogleVisonOCR.TextBox"]:
            """ 獲取全部或指定多邊形內的文字框

            Args:
                polygon (Polygon): 指定多邊形. 若沒有指定就抓取所有文字框
                remove_stack_bool (bool): 是否移除重疊的文字框

            Returns:
                文字框列表
            """
            # 獲取文字框列表: 排除最大的全文文字框
            textBox_list = self.textAnnotations[1:]

            # 篩選出指定多邊形區域中框取到文字框中心點位置的文字框串列
            if polygon is not None:
                textBox_list = [
                    textBox
                    for textBox in textBox_list
                    if polygon.contains(textBox.get_center_point())
                ]

            # 若需要移除重疊的文字框，則遍歷尋找文字框的交集: 若任兩個文字框有交集，選擇去掉面積最小者
            if remove_stack_bool:
                textBox_keep_bool_list = [True] * len(textBox_list)
                for i in range(len(textBox_list)):
                    for j in range(i + 1, len(textBox_list)):
                        textBox_i_polygon = textBox_list[i].get_polygon()
                        textBox_j_polygon = textBox_list[j].get_polygon()

                        # 獲取較大以及較小的文字框編號、文字框區域
                        small_textBox_index = i
                        small_textBox_polygon, big_textBox_polygon = textBox_i_polygon, textBox_j_polygon
                        if textBox_i_polygon.area > textBox_j_polygon.area:
                            small_textBox_index = j
                            small_textBox_polygon, big_textBox_polygon = textBox_j_polygon, textBox_i_polygon

                        # 若較小的文字框面積是 0，則去掉面積最小者
                        if small_textBox_polygon.area == 0:
                            textBox_keep_bool_list[small_textBox_index] = False
                            continue

                        # 計算覆蓋率
                        stack_ratio = small_textBox_polygon.intersection(
                            big_textBox_polygon).area / small_textBox_polygon.area
                        # 若覆蓋綠大於 0.2，則移除較小的文字框
                        if stack_ratio > 0.2:
                            textBox_keep_bool_list[small_textBox_index] = False
                textBox_list = [
                    textBox
                    for textBox, textBox_keep_bool in zip(textBox_list, textBox_keep_bool_list)
                    if textBox_keep_bool
                ]

            return textBox_list

        def get_lineBox_list(
            self,
            textBox_list=None,
            remove_stack_bool=False,
        ) -> List["LineBox"]:
            """ 獲取行文字框串列

            Args:
                textBox_list (List["GoogleVisonOCR.TextBox"]): 文字框列表(可選). 若沒有指定就抓取所有文字框.
                remove_stack_bool (bool): 是否移除重疊的文字框. 預設為 False.

            Returns:
                List["LineBox"]
            """
            if self.lineBox_list_ is not None:
                return self.lineBox_list_

            textBox_list = (
                textBox_list if textBox_list is not None else
                self.get_textBox_list(remove_stack_bool=remove_stack_bool)
            )
            self.lineBox_list_: List[LineBox] = []
            while textBox_list:
                textBox = textBox_list.pop(0)
                lineBox = textBox.get_expanded_lineBox(textBox_list)
                self.lineBox_list_.append(lineBox)
                textBox_list = [
                    textBox for textBox in textBox_list
                    if textBox not in lineBox.textBox_list
                ]
            return self.lineBox_list_

        def get_ocr_str_in_polygon(
            self,
            polygon: Polygon = None,
            textBox_list: List["GoogleVisonOCR.TextBox"] = None,
            i_arr=Point(1, 0),
            remove_stack_bool: bool = True
        ) -> str:
            """ 獲取在指定多邊形內的文字框的文字

            Args:
                polygon (Polygon): 指定多邊形. Default: None.
                textBox_list (List["GoogleVisonOCR.TextBox"]): 指定文字框列表. 若有提供則不會重複計算多邊形內的文字. Default: None.
                i_arr (Point): 水平分量
                remove_stack_bool (bool): 是否移除重疊的文字框. Default: True.

            Returns:
                str: 文字框文字
            """

            # 獲取文字框串列
            if textBox_list is None:
                textBox_list = self.get_textBox_list(
                    polygon=polygon,
                    remove_stack_bool=remove_stack_bool,
                )
            # 由左至右排序文字框，方法: 計算文字框中心位置向量雨水平單位向量的內積，並由小到大排序
            textBox_list.sort(
                key=lambda textBox: (
                    np.inner(
                        textBox.center.arr(),
                        i_arr,
                    ),
                ),
            )
            # 合併文字框串列的文字並傳回
            return "".join([
                textBox.description
                for textBox in textBox_list
            ])

        def get_textBox(
                self,
                startswith: str,) -> Optional["GoogleVisonOCR.TextBox"]:
            """ 獲取指定文字框

            Args:
                startswith (str): 文字開頭

            Returns:
                GoogleVisonOCR.TextBox
            """

            # 遍歷所有文字框 (不要包含最大的全文文字框)
            for textBox in self.textAnnotations[1:]:
                # 若發現有符合搜尋條件的文字框
                if textBox.description.replace(" ", "").startswith(startswith):
                    return textBox

            return None

        def get_textBox_list_by_str_filter(
                self,
                func: Callable[[str], bool],
        ) -> List["GoogleVisonOCR.TextBox"]:
            """ 根據過濾器函數獲取指定文字框

            Args:
                func (Callable[[str], bool]): 文字搜尋條件

            Returns:
                GoogleVisonOCR.TextBox
            """

            # 遍歷所有文字框 (不要包含最大的全文文字框)
            textBox_list = [
                textBox
                for textBox in self.textAnnotations[1:]
                if func(textBox.description)
            ]

            return textBox_list

        def get_ocr_str(self) -> str:
            """ 獲取 ocr 文字

            Returns:
                str
            """
            # 印出第一個文字框(最大的文字框:全文 ocr 內容)
            for textBox in self.textAnnotations:
                return textBox.description
            return ""

        def get_correction_degree(self) -> float:
            """ 根據統計文字框的傾斜角度，輸出建議的修正角度

            Returns:
                float: 修正角度. 範圍: -180 ~ 180
            """
            # 獲取文字框的水平向量串列
            i_arr_list = []
            for textBox in self.textAnnotations:
                i_arr = (textBox.right_top - textBox.left_top)
                i_arr_list.append(
                    i_arr
                )
            # 獲取修正弧度 θ 值串列
            correction_theta_list = [
                np.arctan2(
                    i_arr.y,
                    i_arr.x,
                )
                for i_arr in i_arr_list
            ]
            # 以串列的中位數作為建議的修正角度值
            return np.median(correction_theta_list)*180/np.pi

    class TextDetectionRequest(BaseModel):
        class Image(BaseModel):
            """ 圖片資料
            """
            class Source(BaseModel):
                """ 圖片來源
                """
                imageUri: str

            source: Optional[Source]
            content: Optional[str]

        features: Optional[dict] = dict(
            maxResults=50,
            type="TEXT_DETECTION",
            model="builtin/latest",
            # model="builtin/stable",
        )
        image: Image

        @classmethod
        def from_img_url(cls, img_url: str):
            """ 由圖片 url 建立 TextDetectionRequest
            """
            return cls(
                image=cls.Image(
                    source=cls.Image.Source(
                        imageUri=img_url,
                    ),
                ),
            )

        @classmethod
        def from_img_base64str(cls, img_base64str: str):
            """ 由圖片 base64 字串建立 TextDetectionRequest
            """
            return cls(
                image=cls.Image(
                    content=img_base64str,
                ),
            )

    class TextDetectionRequests(BaseModel):
        requests: List["GoogleVisonOCR.TextDetectionRequest"]

        def _get_res_json(
            self,
            model_str: Literal["builtin/latest", "builtin/stable"] = "builtin/latest",
        ) -> dict:
            """ 送出分析請求，獲得響應 json 字典

            Args:
                model_str:
                    模型版本 (Literal["builtin/latest", "builtin/stable"])
                    Ref. https://cloud.google.com/vision/docs/reference/rest/v1/Feature

            Raises:
                requests.exceptions.HTTPError: 網路連線問題

            Returns:
                dict
            """
            # 若請求圖片數量超過限制，則分段請求
            if len(self.requests) > GoogleVisonOCR.REQUEST_IMGS_MAX_INT:
                return self.__class__(
                    requests=self.requests[:GoogleVisonOCR.REQUEST_IMGS_MAX_INT]
                ) + self.__class__(
                    requests=self.requests[GoogleVisonOCR.REQUEST_IMGS_MAX_INT:]
                )

            # 更新辨識模型版本
            for req in self.requests:
                req.features["model"] = model_str

            # 送出請求
            res = requests.post(
                GoogleVisonOCR.URL,
                json=self.dict(),
            )
            res.raise_for_status()
            # 輸出解析後的文本結果
            return res.json()

        def get_imageTextAnnotation_list(
            self,
            model_str: Literal["builtin/latest", "builtin/stable"] = "builtin/latest",
        ) -> List["GoogleVisonOCR.ImageTextAnnotation"]:
            """ 獲取批次圖片文字辨識結果串列

            Args:
                model_str:
                    模型版本 (Literal["builtin/latest", "builtin/stable"])
                    Ref. https://cloud.google.com/vision/docs/reference/rest/v1/Feature

            Raises:
                requests.exceptions.HTTPError: 網路連線問題

            Returns:
                List[GoogleVisonOCR.ImageTextAnnotation]
            """
            res_json = self._get_res_json(model_str=model_str)
            return [
                GoogleVisonOCR.ImageTextAnnotation.parse_obj(
                    imageTextAnnotation_dict
                )
                for imageTextAnnotation_dict in res_json.get("responses", [])
            ]

        def get_ocr_str_list(
            self,
            model_str: Literal["builtin/latest", "builtin/stable"] = "builtin/latest",
        ) -> List[str]:
            """ 獲取批次 ocr 文字串列 (已皆消除空白字元)

            Args:
                model_str:
                    模型版本 (Literal["builtin/latest", "builtin/stable"])
                    Ref. https://cloud.google.com/vision/docs/reference/rest/v1/Feature

            Raises:
                requests.exceptions.HTTPError: 網路連線問題

            Returns:
                List[str]
            """

            # 輸出解析後的文本結果
            res_json = self._get_res_json(model_str=model_str)
            return [
                result_dict
                .get("fullTextAnnotation", {})
                .get("text", "")
                .replace(" ", "")  # 消除空白字元
                for result_dict in res_json.get("responses", [dict()])
            ]

    @classmethod
    def update_forward_refs(cls):
        """ 更新 pydantic 模型的 forward_refs 使其可用
        """
        cls.ImageTextAnnotation.update_forward_refs()
        cls.TextBox.update_forward_refs()
        cls.TextBoxVertice.update_forward_refs()
        cls.TextBoxPoly.update_forward_refs()
        cls.TextDetectionRequests.update_forward_refs()


# 更新 pydantic 模型的 forward_refs 使其可用
GoogleVisonOCR.update_forward_refs()


class LineBox:
    """ 行文字框
    """

    def __init__(self, textBox_list: List[GoogleVisonOCR.TextBox]) -> None:
        self.textBox_list = sorted(
            textBox_list,
            key=lambda textBox: textBox.center.x,
        )
        self.description = "".join(
            textBox.description
            for textBox in self.textBox_list
        )
        if self.textBox_list:
            self.left_top = self.textBox_list[0].left_top
            self.left_bottom = self.textBox_list[0].left_bottom
            self.right_top = self.textBox_list[-1].right_top
            self.right_bottom = self.textBox_list[-1].right_bottom
            self.center = (self.left_top+self.right_bottom)/2.0
            self.w = int(self.right_bottom.x - self.left_top.x)
            self.h = int(self.right_bottom.y - self.left_top.y)

    def get_multi_line_description(self, sep="") -> str:
        """ 獲取多行文字

        Returns:
            str
        """
        lineBox_str_list = []
        textBox_list = self.textBox_list.copy()
        textBox_list.sort(key=lambda textBox: textBox.center.y)
        while textBox_list:
            textBox = textBox_list.pop(0)
            same_line_textBox_list = [
                other_textBox
                for other_textBox in textBox_list
                if textBox.left_top.y < other_textBox.center.y < textBox.left_bottom.y
            ]+[textBox]
            same_line_textBox_list.sort(key=lambda textBox: textBox.center.x)
            lineBox_str_list.append(
                "".join([
                    same_line_textBox.description
                    for same_line_textBox in same_line_textBox_list
                ])
            )
            textBox_list = [
                textBox_
                for textBox_ in textBox_list
                if textBox_ not in same_line_textBox_list
            ]

        return sep.join(lineBox_str_list)

    def __str__(self) -> str:
        return (
            f"LineBox("
            f"{self.left_top, self.right_top, self.right_bottom, self.left_bottom}"
            f")"
            f": {self.description}"
        )

    def plot(self, ax: plt.Axes) -> None:
        """ 繪製
        """
        if self.textBox_list:
            # 繪製文字框
            ax.add_collection(
                PolyCollection([
                    [
                        [
                            vertice.x,
                            vertice.y
                        ]
                        for vertice in [
                            self.left_top,
                            self.right_top,
                            self.right_bottom,
                            self.left_bottom,
                        ]
                    ]],
                    edgecolors="blue",
                    facecolors="none",
                    linewidths=1,
                ),
            )
            # 繪製文字
            plt.text(
                self.left_top.x,
                self.left_top.y,
                self.description,
                color="blue",
                fontproperties=zh_fp(12),
            )
