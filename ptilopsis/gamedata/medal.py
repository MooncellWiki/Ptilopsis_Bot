"""medal_table.json 的数据模型,对应 FBS/medal_table.fbs。"""

from enum import IntEnum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


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

    model_config = ConfigDict(alias_generator=to_camel)

    id: str
    count: int
    # enum__Torappu_ItemType 的成员名;枚举项近百个且随版本新增,不做强校验
    type: str


class MedalRewardGroupData(BaseModel):
    """clz_Torappu_MedalRewardGroupData"""

    model_config = ConfigDict(alias_generator=to_camel)

    item_list: list[ItemBundle]


class MedalPerData(BaseModel):
    """clz_Torappu_MedalPerData"""

    model_config = ConfigDict(alias_generator=to_camel)

    medal_id: str
    medal_name: str
    medal_type: str
    pre_medal_id_list: list[str] | None
    # MedalRarity 的成员名;为兼容未来新增稀有度保留原始字符串,不做强校验
    rarity: str
    get_method: str | None
    description: str | None
    advanced_medal: str | None
    origin_medal: str | None
    medal_reward_group: list[MedalRewardGroupData]


class MedalGroupData(BaseModel):
    """clz_Torappu_MedalGroupData"""

    model_config = ConfigDict(alias_generator=to_camel)

    group_name: str
    group_desc: str
    medal_id: list[str]


class MedalTypeData(BaseModel):
    """clz_Torappu_MedalTypeData"""

    model_config = ConfigDict(alias_generator=to_camel)

    medal_name: str
    group_data: list[MedalGroupData]


class MedalData(BaseModel):
    """clz_Torappu_MedalData,medal_table.json 的根对象。"""

    model_config = ConfigDict(alias_generator=to_camel)

    medal_list: list[MedalPerData]
    medal_type_data: dict[str, MedalTypeData]
