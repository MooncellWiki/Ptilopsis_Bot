"""item_table.json 的数据模型,对应 FBS/item_table.fbs。"""

from enum import IntEnum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ItemRarity(IntEnum):
    """enum__Torappu_ItemRarity,枚举值即 wiki 侧使用的稀有度序号。"""

    TIER_1 = 0
    TIER_2 = 1
    TIER_3 = 2
    TIER_4 = 3
    TIER_5 = 4
    TIER_6 = 5


class ItemDataBuildingProductInfo(BaseModel):
    """clz_Torappu_ItemData_BuildingProductInfo"""

    model_config = ConfigDict(alias_generator=to_camel)

    # enum__Torappu_BuildingData_RoomType 的成员名;保留字符串以兼容新增房间类型
    room_type: str
    formula_id: str


class ItemData(BaseModel):
    """clz_Torappu_ItemData"""

    model_config = ConfigDict(alias_generator=to_camel)

    item_id: str
    name: str
    description: str | None
    # enum__Torappu_ItemRarity 的成员名;未知成员原样传给 wiki
    rarity: str
    icon_id: str | None
    sort_id: int
    usage: str | None
    obtain_approach: str | None = None
    hide_in_item_get: bool = False
    # enum__Torappu_ItemType 的成员名;枚举项多且随版本新增,不做强校验
    item_type: str
    building_product_list: list[ItemDataBuildingProductInfo]


class InventoryData(BaseModel):
    """clz_Torappu_InventoryData,item_table.json 的根对象。"""

    items: dict[str, ItemData]
