"""roguelike_table.json(初代集成战略,已停更)的数据模型(手写)。

这张旧表没有 FBS schema,只建模 ``stages``,供历史脚本查关卡代号 / 名称用;
现行集成战略数据在 ``roguelike_topic_table``。
"""

from ptilopsis.gamedata._base import GameDataModel

__all__ = ["RoguelikeStage", "RoguelikeTable"]


class RoguelikeStage(GameDataModel):
    """clz_Torappu_RoguelikeStageData"""

    id: str | None = None
    linked_stage_id: str | None = None
    level_id: str | None = None
    code: str | None = None
    name: str | None = None
    loading_pic_id: str | None = None
    description: str | None = None
    elite_desc: str | None = None
    is_boss: int = 0
    is_elite: int = 0
    # enum__Torappu_LevelData_Difficulty 的成员名
    difficulty: str = "NONE"


class RoguelikeTable(GameDataModel):
    """clz_Torappu_RoguelikeTable(仅 stages)"""

    stages: dict[str, RoguelikeStage] | None = None
