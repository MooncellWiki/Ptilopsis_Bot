"""uniequip_table.json 的数据模型,对应 FBS/uniequip_table.fbs。"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class UniEquipType(StrEnum):
    """enum__Torappu_UniEquipType 在 JSON 中使用的枚举成员名。"""

    INITIAL = "INITIAL"
    ADVANCED = "ADVANCED"


class UniEquipData(BaseModel):
    """clz_Torappu_UniEquipData。"""

    model_config = ConfigDict(alias_generator=to_camel)

    uni_equip_name: str
    type_name_1: str
    type_name_2: str


class UniEquipTrack(BaseModel):
    """clz_Torappu_UniEquipTrack。"""

    model_config = ConfigDict(alias_generator=to_camel)

    char_id: str
    equip_id: str
    type: UniEquipType
    archive_show_time_end: int


class UniEquipTimeInfo(BaseModel):
    """clz_Torappu_UniEquipTimeInfo。"""

    model_config = ConfigDict(alias_generator=to_camel)

    time_stamp: int
    track_list: list[UniEquipTrack]


class UniEquipTable(BaseModel):
    """clz_Torappu_UniEquipTable, uniequip_table.json 的根对象。"""

    model_config = ConfigDict(alias_generator=to_camel)

    equip_dict: dict[str, UniEquipData]
    equip_track_dict: list[UniEquipTimeInfo]
