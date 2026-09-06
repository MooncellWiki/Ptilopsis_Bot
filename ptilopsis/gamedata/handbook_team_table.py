"""handbook_team_table.json 的数据模型。

由 scripts/gen_gamedata_models.py 从 FBS/handbook_team_table.fbs 生成,请勿手改;
字段语义见 dump.cs 里的同名类。
"""

from __future__ import annotations

from pydantic import TypeAdapter

from ptilopsis.gamedata._base import GameDataModel


class HandbookTeamData(GameDataModel):
    """clz_Torappu_HandbookTeamData"""

    power_id: str | None = None
    order_num: int = 0
    power_level: int = 0
    power_name: str | None = None
    power_code: str | None = None
    color: str | None = None
    is_limited: bool = False
    is_raw: bool = False


# root_type clz_Torappu_SimpleKVTable_clz_Torappu_HandbookTeamData
# JSON 里去掉了外层的 handbook_teams,直接是 {id: ...}
HandbookTeamTable = TypeAdapter(dict[str, HandbookTeamData])


HandbookTeamData.model_rebuild()
