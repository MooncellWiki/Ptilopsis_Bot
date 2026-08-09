"""medal_table.json 的数据模型,对应 FBS/medal_table.fbs。"""

from enum import IntEnum

from pydantic import BaseModel, Field


class MedalRarity(IntEnum):
    """enum__Torappu_MedalRarity,枚举值即 wiki 侧使用的稀有度序号。"""

    T1 = 0
    T1D5 = 1
    T2 = 2
    T2D5 = 3
    T3 = 4
    T3D5 = 5


class ItemBundle(BaseModel):
    """clz_Torappu_ItemBundle"""

    id: str
    count: int
    # enum__Torappu_ItemType 的成员名;枚举项近百个且随版本新增,不做强校验
    type: str


class MedalRewardGroupData(BaseModel):
    """clz_Torappu_MedalRewardGroupData"""

    item_list: list[ItemBundle] = Field(alias="itemList")


class MedalPerData(BaseModel):
    """clz_Torappu_MedalPerData"""

    medal_id: str = Field(alias="medalId")
    medal_name: str = Field(alias="medalName")
    medal_type: str = Field(alias="medalType")
    pre_medal_ids: list[str] = Field(alias="preMedalIdList")
    # MedalRarity 的成员名;为兼容未来新增稀有度保留原始字符串,不做强校验
    rarity: str
    get_method: str | None = Field(alias="getMethod")
    description: str | None
    advanced_medal: str | None = Field(alias="advancedMedal")
    origin_medal: str | None = Field(alias="originMedal")
    reward_groups: list[MedalRewardGroupData] = Field(alias="medalRewardGroup")


class MedalGroupData(BaseModel):
    """clz_Torappu_MedalGroupData"""

    group_name: str = Field(alias="groupName")
    group_desc: str = Field(alias="groupDesc")
    medal_ids: list[str] = Field(alias="medalId")


class MedalTypeData(BaseModel):
    """clz_Torappu_MedalTypeData"""

    medal_name: str = Field(alias="medalName")
    group_data: list[MedalGroupData] = Field(alias="groupData")


class MedalData(BaseModel):
    """clz_Torappu_MedalData,medal_table.json 的根对象。"""

    medal_list: list[MedalPerData] = Field(alias="medalList")
    medal_type_data: dict[str, MedalTypeData] = Field(alias="medalTypeData")
