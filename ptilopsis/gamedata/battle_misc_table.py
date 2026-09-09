"""battle/battle_misc_table.json 的数据模型(手写)。

battle_misc_table 不是 FlatBuffers 表,OpenArknightsFBS 里没有它的 schema;
这里只建模 job 用到的 ``levelScenePairs``(关卡 → 实际加载的场景 / 地图预览),
其余键(``effectBlacklist`` / ``miscConfig`` …)原样忽略。
"""

from ptilopsis.gamedata._base import GameDataModel

__all__ = ["BattleMiscTable", "LevelScenePair"]


class LevelScenePair(GameDataModel):
    """clz_Torappu_Battle_LevelScenePair"""

    level_id: str | None = None
    scene_id: str | None = None
    hooked_map_preview_id: str | None = None


class BattleMiscTable(GameDataModel):
    """clz_Torappu_Battle_BattleMiscTable"""

    level_scene_pairs: dict[str, LevelScenePair] | None = None
