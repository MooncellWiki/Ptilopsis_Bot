"""building_data.json 的数据模型,对应 FBS/building_data.fbs。"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ItemBundle(BaseModel):
    """clz_Torappu_ItemBundle"""

    id: str
    count: int


class BuildingDataManufactFormulaUnlockRoom(BaseModel):
    """clz_Torappu_BuildingData_ManufactFormula_UnlockRoom"""

    model_config = ConfigDict(alias_generator=to_camel)

    room_level: int


class BuildingDataManufactFormula(BaseModel):
    """clz_Torappu_BuildingData_ManufactFormula"""

    model_config = ConfigDict(alias_generator=to_camel)

    item_id: str
    count: int
    weight: int
    cost_point: int
    costs: list[ItemBundle]
    require_rooms: list[BuildingDataManufactFormulaUnlockRoom]


class BuildingDataWorkshopExtraWeightItem(BaseModel):
    """clz_Torappu_BuildingData_WorkshopExtraWeightItem"""

    model_config = ConfigDict(alias_generator=to_camel)

    weight: int
    item_id: str


class BuildingDataWorkshopFormulaUnlockRoom(BaseModel):
    """clz_Torappu_BuildingData_WorkshopFormula_UnlockRoom"""

    model_config = ConfigDict(alias_generator=to_camel)

    room_level: int


class BuildingDataWorkshopFormulaUnlockStage(BaseModel):
    """clz_Torappu_BuildingData_WorkshopFormula_UnlockStage"""

    model_config = ConfigDict(alias_generator=to_camel)

    stage_id: str
    rank: int


class BuildingDataWorkshopFormula(BaseModel):
    """clz_Torappu_BuildingData_WorkshopFormula"""

    model_config = ConfigDict(alias_generator=to_camel)

    item_id: str
    count: int
    gold_cost: int
    ap_cost: int
    extra_outcome_rate: float
    extra_outcome_group: list[BuildingDataWorkshopExtraWeightItem]
    costs: list[ItemBundle]
    require_rooms: list[BuildingDataWorkshopFormulaUnlockRoom]
    require_stages: list[BuildingDataWorkshopFormulaUnlockStage]


class BuildingData(BaseModel):
    """clz_Torappu_BuildingData,仅建模道具 job 使用的配方字段。"""

    model_config = ConfigDict(alias_generator=to_camel)

    manufact_formulas: dict[str, BuildingDataManufactFormula]
    workshop_formulas: dict[str, BuildingDataWorkshopFormula]
