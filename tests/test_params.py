"""params 里各依赖的解析:表名注册、海外服 region、关卡加载器、敌人索引。"""

from typing import Annotated, Any

import pytest

from ptilopsis.gamedata.character_table import CharacterData
from ptilopsis.gamedata.enemy_database import EnemyDatabaseEnemyLevel
from ptilopsis.gamedata.level_data import LevelData
from ptilopsis.jobs import params
from ptilopsis.utils.data import GameData
from ptilopsis.utils.di import Resolver, analyze
from ptilopsis.utils.job import PROVIDED_TYPES

pytestmark = pytest.mark.anyio


class FakeGameData:
    def __init__(self) -> None:
        self.reads: list[tuple[str, str]] = []

    async def get(self, path: str, region: str = "CN") -> Any:
        self.reads.append((path, region))
        if path.endswith("character_table.json"):
            return {"char_1": {"name": f"阿米娅-{region}", "rarity": "TIER_5"}}
        if path.endswith("enemy_database.json"):
            return {
                "enemies": [
                    {"Key": "enemy_a", "Value": [{"level": 0}, {"level": 1}]},
                    {"Key": None, "Value": []},
                ]
            }
        if path.endswith("gamedata_const.json"):
            return {"richTextStyles": {"ba.vup": "<color=#0098DC>{0}</color>"}}
        if path.startswith("levels/"):
            return {"options": {"characterLimit": 6}, "waves": []}
        raise AssertionError(path)

    async def list_files(self, path: str, region: str = "CN") -> list[str]:
        return [
            "levels/obt/main/level_main_01-01.json",
            "levels/obt/main/readme.txt",
        ]


async def solve(dependency: Any, data: Any) -> Any:
    marker = (
        dependency.__metadata__[0]
        if hasattr(dependency, "__metadata__")
        else dependency
    )
    dependant = analyze(marker.dependency, PROVIDED_TYPES)
    return await Resolver({GameData: data}).solve(dependant)


def test_every_registered_table_has_a_path_and_model() -> None:
    for name, spec in params.TABLES.items():
        assert spec.path.endswith(".json"), name
        assert hasattr(spec.model, "validate_python") or hasattr(
            spec.model, "model_validate"
        ), name


async def test_table_alias_validates_into_models() -> None:
    data = FakeGameData()
    table = await solve(params.CharacterTable, data)
    assert isinstance(table["char_1"], CharacterData)
    assert table["char_1"].name == "阿米娅-CN"
    assert data.reads == [("excel/character_table.json", "CN")]


async def test_table_with_region_reads_that_server() -> None:
    data = FakeGameData()
    dep = Annotated[dict[str, CharacterData], params.table("character_table", "JP")]
    table = await solve(dep, data)
    assert table["char_1"].name == "阿米娅-JP"
    assert data.reads == [("excel/character_table.json", "JP")]


def test_unknown_table_name_is_rejected() -> None:
    with pytest.raises(KeyError):
        params.table("no_such_table")


async def test_level_loader_reads_by_id_and_lists_ids() -> None:
    data = FakeGameData()
    levels = await solve(params.Levels, data)
    level = await levels("Obt/Main/level_main_01-01")
    assert isinstance(level, LevelData)
    assert level.options is not None and level.options.character_limit == 6
    assert data.reads == [("levels/obt/main/level_main_01-01.json", "CN")]
    assert await levels.raw("Obt/Main/level_main_01-01") == {
        "options": {"characterLimit": 6},
        "waves": [],
    }
    assert await levels.list_ids("levels/obt/main") == ["obt/main/level_main_01-01"]


async def test_enemy_levels_index_skips_entries_without_key() -> None:
    index = await solve(params.EnemyLevels, FakeGameData())
    assert list(index) == ["enemy_a"]
    assert [lv.level for lv in index["enemy_a"]] == [0, 1]
    assert isinstance(index["enemy_a"][0], EnemyDatabaseEnemyLevel)


async def test_rich_text_variants_use_typed_gamedata_const() -> None:
    data = FakeGameData()
    assert (await solve(params.RichText, data)).compile("<@ba.vup>x</>") == (
        "{{color|#0098DC|x}}"
    )
    assert (await solve(params.RichTextHtml, data)).compile("<@ba.vup>x</>") == (
        '<span style="color:#0098DC;">x</span>'
    )
