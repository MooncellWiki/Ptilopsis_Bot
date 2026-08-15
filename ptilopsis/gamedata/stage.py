"""stage_table.json 的数据模型,对应 FBS/stage_table.fbs。

所有字段都带默认值。整张表是在遍历关卡之前一次性校验的,若字段声明为必填,
上游任何一个关卡的 schema 漂移都会让 StageTable.model_validate 整体失败,
进而导致全部三千多个关卡一个都产不出来。带上默认值后,漂移只会退化成
单个关卡的单个字段缺失,与重构前逐字段访问的容错程度一致。

默认值只在键缺失时生效,键存在而值为 null 仍然会校验失败——上游把某个字段
从有值改成 null 比整个删掉更常见,所以 StageModel 在校验前先把值为 None 的键
去掉,让它和"键不存在"走同一条退化路径。这要求本模块的字段一律带默认值:
声明成 `str | None` 却不给默认值的字段会因此变成必填。
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel


class StageModel(BaseModel):
    """本模块所有模型的基类,统一 camelCase 别名与 null 的退化方式。"""

    model_config = ConfigDict(alias_generator=to_camel)

    @model_validator(mode="before")
    @classmethod
    def _drop_null_values(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        return {key: value for key, value in data.items() if value is not None}


class StageDataConditionDesc(StageModel):
    """clz_Torappu_StageData_ConditionDesc。"""

    stage_id: str = ""
    # enum__Torappu_PlayerBattleRank 的成员名
    complete_state: str = ""


class StageDataDisplayDetailRewards(StageModel):
    """clz_Torappu_StageData_DisplayDetailRewards。"""

    # 两个枚举在历史数据里也曾以数字出现,保留兼容性
    occ_percent: int | str = ""
    type: str = ""
    id: str = ""
    # 缺省值经 parse_drop_type 会得到 "None",该分组不会被渲染
    drop_type: int | str = "NONE"


class StageDataStageDropInfo(StageModel):
    """clz_Torappu_StageData_StageDropInfo 中 job 使用的字段。"""

    display_detail_rewards: list[StageDataDisplayDetailRewards] = []


class StageData(StageModel):
    """clz_Torappu_StageData 中 stage job 使用的字段。"""

    stage_type: str = ""
    difficulty: str = ""
    diff_group: str = ""
    unlock_condition: list[StageDataConditionDesc] = []
    stage_id: str = ""
    level_id: str | None = None
    zone_id: str = ""
    code: str | None = None
    name: str | None = None
    description: str | None = None
    hard_staged_id: str | None = None
    danger_level: str | None = None
    can_practice: bool = False
    ap_cost: int = 0
    practice_ticket_cost: int = 0
    hilight_mark: bool = False
    boss_mark: bool = False
    appearance_style: str = ""
    stage_drop_info: StageDataStageDropInfo = StageDataStageDropInfo()


class TileAppendInfo(StageModel):
    """clz_Torappu_TileAppendInfo 中 stage job 使用的字段。"""

    name: str = ""


class StageTable(StageModel):
    """clz_Torappu_StageTable 中 stage job 使用的字段。"""

    stages: dict[str, StageData] = {}
    tile_info: dict[str, TileAppendInfo] = {}
