import numpy as np
from pydantic import BaseModel, Field

from libs.utils import StrictnessIntEnum

PHOTOGRAPHIC_SCORE_SCORE_THRESHOLD = 4.0
MATCH_AREA_N_THRESHOLD = 10
MATCH_SCORE_THRESHOLD = 0.993


class Out(BaseModel):
    """ PhotoShop 加工痕跡偵測結果
    """
    has_ps_bool: bool = Field(
        False,
        description="是否有可疑P圖痕跡",
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
    def get_example(cls) -> "Out":
        return cls(
            match_score_list=np.round(
                np.linspace(0.998, 0.980, 100),
                3,
            ),
        )
