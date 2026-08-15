"""building_data.json 的数据模型,对应 FBS/building_data.fbs。"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class RoomData(BaseModel):
    """clz_Torappu_BuildingData_RoomData。"""

    model_config = ConfigDict(alias_generator=to_camel)

    name: str


class BuildingBuff(BaseModel):
    """clz_Torappu_BuildingData_BuildingBuff。"""

    model_config = ConfigDict(alias_generator=to_camel)

    buff_id: str
    buff_name: str
    skill_icon: str
    sort_id: int
    # enum__Torappu_BuildingData_RoomType 的成员名;保留原始字符串以兼容新增房间
    room_type: str
    description: str


class BuildingData(BaseModel):
    """clz_Torappu_BuildingData,building_data.json 的根对象。"""

    model_config = ConfigDict(alias_generator=to_camel)

    rooms: dict[str, RoomData]
    buffs: dict[str, BuildingBuff]
