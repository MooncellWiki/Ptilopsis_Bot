"""range_table.json 的数据模型(手写)。

range_table 不是 FlatBuffers 表,OpenArknightsFBS 里没有它的 schema,
这里按客户端 ``Torappu.RangeData`` 手写,空值约定与生成模型一致(见 ``_base``)。
"""

from pydantic import TypeAdapter

from ptilopsis.gamedata._base import GameDataModel

__all__ = ["GridPosition", "RangeData", "RangeTable"]


class GridPosition(GameDataModel):
    """clz_Torappu_GridPosition"""

    row: int = 0
    col: int = 0


class RangeData(GameDataModel):
    """clz_Torappu_RangeData"""

    id: str | None = None
    # enum__Torappu_RangeData_RangeDirection 的数值
    direction: int = 0
    grids: list[GridPosition] | None = None


RangeTable = TypeAdapter(dict[str, RangeData])
