"""job 函数可以直接注入的现成依赖(见 :mod:`ptilopsis.utils.job`)。

用法::

    from typing import Annotated

    from ptilopsis.gamedata.character_table import CharacterData
    from ptilopsis.jobs.params import (
        CharacterTable, CharIdTable, ItemTable, Levels, RichText, category, table,
    )

    @job
    async def run(
        wiki: Wiki,
        character_table: CharacterTable,
        item_table: ItemTable,
        character_table_jp: Annotated[
            dict[str, CharacterData], table("character_table", "JP")
        ],
        levels: Levels,
        rts: RichText,
        char_list: Annotated[list[str], category("分类:干员")],
    ) -> None:
        level = await levels(stage.level_id)
        ...

每张表都注册在 :data:`TABLES` 里,``XxxTable`` 这类别名就是"读取 + 校验成
``ptilopsis.gamedata`` 里对应模型"的依赖;需要海外服数据时用 :func:`table`
指定 region。同一张表在一次 job 运行里只校验一次;原始 JSON 由 GameData 跨 job 缓存。
"""

import csv
import io
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any

from ptilopsis.gamedata import (
    activity_table,
    battle_equip_table,
    battle_misc_table,
    building_data,
    campaign_table,
    char_patch_table,
    character_table,
    charword_table,
    crisis_v2_table,
    enemy_database,
    enemy_handbook_table,
    gamedata_const,
    handbook_info_table,
    handbook_team_table,
    item_table,
    level_data,
    medal_table,
    mission_table,
    range_table,
    roguelike_table,
    roguelike_topic_table,
    sandbox_perm_table,
    shop_client_table,
    skill_table,
    skin_table,
    stage_table,
    story_review_meta_table,
    story_review_table,
    uniequip_table,
    zone_table,
)
from ptilopsis.gamedata.enemy_util import index_enemy_levels
from ptilopsis.utils import richtext
from ptilopsis.utils.data import GameData
from ptilopsis.utils.di import Depends
from ptilopsis.utils.wiki import Wiki

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "TABLES",
    "ActivityTable",
    "BattleEquipTable",
    "BattleMiscTable",
    "BuildingData",
    "CampaignTable",
    "CharIdTable",
    "CharPatchTable",
    "CharacterTable",
    "CharwordTable",
    "CrisisV2Table",
    "EnemyDatabase",
    "EnemyHandbookTable",
    "EnemyLevels",
    "GamedataConst",
    "HandbookInfoTable",
    "HandbookTeamTable",
    "ItemTable",
    "LevelLoader",
    "Levels",
    "MedalTable",
    "MissionTable",
    "RangeTable",
    "RichText",
    "RichTextHtml",
    "RoguelikeTable",
    "RoguelikeTopicTable",
    "SandboxPermTable",
    "ShopClientTable",
    "SkillTable",
    "SkinTable",
    "StageTable",
    "StoryReviewMetaTable",
    "StoryReviewTable",
    "TableSpec",
    "UniEquipTable",
    "ZoneTable",
    "category",
    "gamedata",
    "gamedata_text",
    "table",
]


def gamedata(path: str, model: Any = None, region: str = "CN") -> Any:
    """``gamedata/<path>`` 解码后的 JSON;给 ``model`` 时校验成 pydantic 模型
    (``BaseModel`` 或 ``TypeAdapter`` 都可以)。

    已建模的表用 :func:`table` / ``XxxTable`` 别名;这个函数留给临时路径。
    """

    validate: Callable[[Any], Any] | None = None
    if model is not None:
        validate = getattr(model, "validate_python", None) or model.model_validate

    async def dependency(data: GameData) -> Any:
        raw = await data.get(path, region)
        return validate(raw) if validate is not None else raw

    dependency.__qualname__ = f"gamedata({path!r}, region={region!r})"
    return Depends(dependency)


def gamedata_text(path: str, region: str = "CN") -> Any:
    """``gamedata/<path>`` 的原始文本(剧情等非 JSON 文件)。"""

    async def dependency(data: GameData) -> str:
        return await data.get_txt(path, region)

    dependency.__qualname__ = f"gamedata_text({path!r})"
    return Depends(dependency)


# ---- 各表 ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TableSpec:
    """一张表在 gamedata 里的路径与校验它的模型(``BaseModel`` 或 ``TypeAdapter``)。"""

    path: str
    model: Any


TABLES: dict[str, TableSpec] = {
    "activity_table": TableSpec(
        "excel/activity_table.json", activity_table.ActivityTable
    ),
    "battle_equip_table": TableSpec(
        "excel/battle_equip_table.json", battle_equip_table.BattleEquipTable
    ),
    "battle_misc_table": TableSpec(
        "battle/battle_misc_table.json", battle_misc_table.BattleMiscTable
    ),
    "building_data": TableSpec("excel/building_data.json", building_data.BuildingData),
    "campaign_table": TableSpec(
        "excel/campaign_table.json", campaign_table.CampaignTable
    ),
    "char_patch_table": TableSpec(
        "excel/char_patch_table.json", char_patch_table.CharPatchTable
    ),
    "character_table": TableSpec(
        "excel/character_table.json", character_table.CharacterTable
    ),
    "charword_table": TableSpec(
        "excel/charword_table.json", charword_table.CharwordTable
    ),
    "crisis_v2_table": TableSpec(
        "excel/crisis_v2_table.json", crisis_v2_table.CrisisV2Table
    ),
    "enemy_database": TableSpec(
        "levels/enemydata/enemy_database.json", enemy_database.EnemyDatabase
    ),
    "enemy_handbook_table": TableSpec(
        "excel/enemy_handbook_table.json", enemy_handbook_table.EnemyHandbookTable
    ),
    "gamedata_const": TableSpec(
        "excel/gamedata_const.json", gamedata_const.GamedataConst
    ),
    "handbook_info_table": TableSpec(
        "excel/handbook_info_table.json", handbook_info_table.HandbookInfoTable
    ),
    "handbook_team_table": TableSpec(
        "excel/handbook_team_table.json", handbook_team_table.HandbookTeamTable
    ),
    "item_table": TableSpec("excel/item_table.json", item_table.ItemTable),
    "medal_table": TableSpec("excel/medal_table.json", medal_table.MedalTable),
    "mission_table": TableSpec("excel/mission_table.json", mission_table.MissionTable),
    "range_table": TableSpec("excel/range_table.json", range_table.RangeTable),
    "roguelike_table": TableSpec(
        "excel/roguelike_table.json", roguelike_table.RoguelikeTable
    ),
    "roguelike_topic_table": TableSpec(
        "excel/roguelike_topic_table.json", roguelike_topic_table.RoguelikeTopicTable
    ),
    "sandbox_perm_table": TableSpec(
        "excel/sandbox_perm_table.json", sandbox_perm_table.SandboxPermTable
    ),
    "shop_client_table": TableSpec(
        "excel/shop_client_table.json", shop_client_table.ShopClientTable
    ),
    "skill_table": TableSpec("excel/skill_table.json", skill_table.SkillTable),
    "skin_table": TableSpec("excel/skin_table.json", skin_table.SkinTable),
    "stage_table": TableSpec("excel/stage_table.json", stage_table.StageTable),
    "story_review_meta_table": TableSpec(
        "excel/story_review_meta_table.json",
        story_review_meta_table.StoryReviewMetaTable,
    ),
    "story_review_table": TableSpec(
        "excel/story_review_table.json", story_review_table.StoryReviewTable
    ),
    "uniequip_table": TableSpec(
        "excel/uniequip_table.json", uniequip_table.UniEquipTable
    ),
    "zone_table": TableSpec("excel/zone_table.json", zone_table.ZoneTable),
}
"""表名 → 路径与模型。新表在 ``ptilopsis/gamedata`` 生成好模型后登记到这里。"""


def table(name: str, region: str = "CN") -> Any:
    """按表名注入校验好的模型;``region`` 指定服务器(CN / JP / US / KR / TW)。"""

    spec = TABLES[name]
    return gamedata(spec.path, spec.model, region)


ActivityTable = Annotated[activity_table.ActivityTable, table("activity_table")]
BattleEquipTable = Annotated[
    dict[str, battle_equip_table.BattleEquipPack], table("battle_equip_table")
]
BattleMiscTable = Annotated[
    battle_misc_table.BattleMiscTable, table("battle_misc_table")
]
BuildingData = Annotated[building_data.BuildingData, table("building_data")]
CampaignTable = Annotated[campaign_table.CampaignTable, table("campaign_table")]
CharPatchTable = Annotated[char_patch_table.CharPatchData, table("char_patch_table")]
CharacterTable = Annotated[
    dict[str, character_table.CharacterData], table("character_table")
]
CharwordTable = Annotated[charword_table.CharWordTable, table("charword_table")]
CrisisV2Table = Annotated[crisis_v2_table.CrisisV2SharedData, table("crisis_v2_table")]
EnemyDatabase = Annotated[enemy_database.EnemyDatabase, table("enemy_database")]
EnemyHandbookTable = Annotated[
    enemy_handbook_table.EnemyHandBookDataGroup, table("enemy_handbook_table")
]
GamedataConst = Annotated[gamedata_const.GameDataConsts, table("gamedata_const")]
HandbookInfoTable = Annotated[
    handbook_info_table.HandbookInfoTable, table("handbook_info_table")
]
HandbookTeamTable = Annotated[
    dict[str, handbook_team_table.HandbookTeamData], table("handbook_team_table")
]
ItemTable = Annotated[item_table.InventoryData, table("item_table")]
MedalTable = Annotated[medal_table.MedalData, table("medal_table")]
MissionTable = Annotated[mission_table.MissionTable, table("mission_table")]
RangeTable = Annotated[dict[str, range_table.RangeData], table("range_table")]
RoguelikeTable = Annotated[roguelike_table.RoguelikeTable, table("roguelike_table")]
RoguelikeTopicTable = Annotated[
    roguelike_topic_table.RoguelikeTopicTable, table("roguelike_topic_table")
]
SandboxPermTable = Annotated[
    sandbox_perm_table.SandboxPermTable, table("sandbox_perm_table")
]
ShopClientTable = Annotated[
    shop_client_table.ShopClientData, table("shop_client_table")
]
SkillTable = Annotated[dict[str, skill_table.SkillDataBundle], table("skill_table")]
SkinTable = Annotated[skin_table.SkinTable, table("skin_table")]
StageTable = Annotated[stage_table.StageTable, table("stage_table")]
StoryReviewMetaTable = Annotated[
    story_review_meta_table.StoryReviewMetaTable, table("story_review_meta_table")
]
StoryReviewTable = Annotated[
    dict[str, story_review_table.StoryReviewGroupClientData],
    table("story_review_table"),
]
UniEquipTable = Annotated[uniequip_table.UniEquipTable, table("uniequip_table")]
ZoneTable = Annotated[zone_table.ZoneTable, table("zone_table")]


# ---- 关卡文件 -----------------------------------------------------------


class LevelLoader:
    """按 ``levelId`` 读取并校验 ``levels/<levelId>.json``(地图、波次、预设编队)。

    关卡文件有近三千个,job 只读自己要用的那些,所以不像整表那样预先注入,
    而是注入这个加载器按需读取。
    """

    def __init__(self, data: GameData, region: str = "CN") -> None:
        self._data = data
        self._region = region

    @staticmethod
    def path(level_id: str) -> str:
        return f"levels/{level_id.lower()}.json"

    async def __call__(self, level_id: str) -> level_data.LevelData:
        return level_data.LevelData.model_validate(await self.raw(level_id))

    async def raw(self, level_id: str) -> dict[str, Any]:
        """未经校验的原始 JSON,给要把整个文件原样发布到 wiki 的 job 用。"""

        return await self._data.get(self.path(level_id), self._region)

    async def prefetch(self, level_ids: Iterable[str]) -> None:
        """并发把这些关卡文件下载进缓存,之后逐个读取不再走网络。"""

        await self._data.prefetch(
            (self.path(level_id) for level_id in level_ids), self._region
        )

    async def list_ids(self, path: str) -> list[str]:
        """``gamedata/<path>`` 下全部关卡文件的 ``levelId``(相对 levels/ 的路径)。"""

        ids = []
        for file in await self._data.list_files(path, self._region):
            if file.startswith("levels/") and file.endswith(".json"):
                ids.append(file[len("levels/") : -len(".json")])
        return ids


def _level_loader(data: GameData) -> LevelLoader:
    return LevelLoader(data)


Levels = Annotated[LevelLoader, Depends(_level_loader)]
"""按 levelId 读取关卡文件的加载器。"""


def _enemy_levels(
    database: EnemyDatabase,
) -> dict[str, list[enemy_database.EnemyDatabaseEnemyLevel]]:
    return index_enemy_levels(database)


EnemyLevels = Annotated[
    dict[str, list[enemy_database.EnemyDatabaseEnemyLevel]], Depends(_enemy_levels)
]
"""enemy_database 按敌人 id 索引:``{enemyId: [level 0, level 1, ...]}``。"""


# ---- 富文本 -------------------------------------------------------------


def _rich_text(consts: GamedataConst) -> richtext.RichText:
    return richtext.RichText.from_gamedata_const(consts, richtext.WikiRenderer())


RichText = Annotated[richtext.RichText, Depends(_rich_text)]
"""按 gamedata_const 构造的富文本转换器,输出 wiki 模板。"""


def _rich_text_html(consts: GamedataConst) -> richtext.RichText:
    return richtext.RichText.from_gamedata_const(consts, richtext.HtmlRenderer())


RichTextHtml = Annotated[richtext.RichText, Depends(_rich_text_html)]
"""输出内联 HTML 的富文本转换器,给前端脚本消费的 JSON 页面用。"""


# ---- wiki --------------------------------------------------------------


async def _char_id_table(wiki: Wiki) -> dict[str, dict[str, Any]]:
    """wiki 上维护的 ``干员一览/干员id`` 表:``{干员名: {id, approach, date}}``。"""

    reader = csv.DictReader(io.StringIO(await wiki.read("干员一览/干员id")))
    return {
        row["name"]: {
            "id": int(row["sortId"]),
            "approach": row["approach"],
            "date": row["date"],
        }
        for row in reader
    }


CharIdTable = Annotated[dict[str, dict[str, Any]], Depends(_char_id_table)]
"""``干员一览/干员id`` 解析后的干员序号 / 获得方式 / 上线时间。"""


def category(name: str) -> Any:
    """wiki 分类 ``name`` 下的全部页面标题。"""

    async def dependency(wiki: Wiki) -> list[str]:
        return await wiki.category(name)

    dependency.__qualname__ = f"category({name!r})"
    return Depends(dependency)
