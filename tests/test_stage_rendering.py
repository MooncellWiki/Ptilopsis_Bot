import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter

from ptilopsis.gamedata.building_data import BuildingData
from ptilopsis.gamedata.character_table import CharacterData, CharacterTable
from ptilopsis.gamedata.enemy_database import EnemyDatabase, EnemyDatabaseEnemyLevel
from ptilopsis.gamedata.enemy_handbook_table import EnemyHandBookData
from ptilopsis.gamedata.enemy_util import index_enemy_levels
from ptilopsis.gamedata.item_table import InventoryData
from ptilopsis.gamedata.level_data import LevelData
from ptilopsis.gamedata.roguelike_topic_table import RoguelikeGameStageData
from ptilopsis.gamedata.sandbox_perm_table import SandboxV2StageData
from ptilopsis.gamedata.skill_table import SkillDataBundle, SkillTable
from ptilopsis.gamedata.stage_table import StageData, StageTable
from ptilopsis.gamedata.zone_table import ZoneTable
from ptilopsis.jobs.stage import (
    BasicPageView,
    BasicStageView,
    CampaignPageView,
    CampaignProgressItemView,
    CampaignProgressRowView,
    CampaignProgressView,
    CampaignStageView,
    NormalPageView,
    RoguelikePageView,
    build_4star_stage,
    build_enemies,
    build_normal_stage,
    build_roguelike_4star_stage,
    build_roguelike_stage,
    build_sandbox_v2_stage,
    build_squad_sections,
    build_tile_effects,
    render_assault_stage,
    render_basic_page,
    render_basic_stage,
    render_campaign_page,
    render_normal_page,
    render_roguelike_page,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "stage"
GOLDEN_DIR = Path(__file__).parent / "golden" / "stage"

EnemyTable = TypeAdapter(dict[str, EnemyHandBookData])


def stub_compile_rich_text(text: str) -> str:
    return f"[RTS]{text}"


@dataclass
class Fixture:
    """basic.json 校验成生成模型后的各张表;raw 留给要先改写字段再校验的用例。"""

    raw: dict[str, Any]
    stage_table: StageTable
    zone_table: ZoneTable
    character_table: dict[str, CharacterData]
    skill_table: dict[str, SkillDataBundle]
    building_data: BuildingData
    item_table: InventoryData
    enemy_table: dict[str, EnemyHandBookData]
    enemy_levels: dict[str, list[EnemyDatabaseEnemyLevel]]
    level: LevelData


def load_fixture() -> Fixture:
    raw = json.loads((FIXTURE_DIR / "basic.json").read_text(encoding="utf-8"))
    return Fixture(
        raw=raw,
        stage_table=StageTable.model_validate(raw["stage_table"]),
        zone_table=ZoneTable.model_validate(raw["zone_table"]),
        character_table=CharacterTable.validate_python(raw["character_table"]),
        skill_table=SkillTable.validate_python(raw["skill_table"]),
        building_data=BuildingData.model_validate(raw["building_data"]),
        item_table=InventoryData.model_validate(raw["item_table"]),
        enemy_table=EnemyTable.validate_python(raw["enemy_table"]),
        enemy_levels=index_enemy_levels(
            EnemyDatabase.model_validate(raw["enemy_database"])
        ),
        level=LevelData.model_validate(raw["level_table"]),
    )


def stage_of(table: StageTable, key: str) -> StageData:
    assert table.stages is not None
    return table.stages[key]


def typed_table(fixture: Fixture, **overrides) -> StageTable:
    """按 overrides 改写普通关卡后校验成 StageTable。"""

    stage_table = copy.deepcopy(fixture.raw["stage_table"])
    stage_table["stages"]["normal"].update(overrides)
    return StageTable.model_validate(stage_table)


def normal_stage_with(fixture: Fixture, **overrides) -> str:
    """按 overrides 改写普通关卡后渲染,用于逐参数比对。"""

    table = typed_table(fixture, **overrides)
    return render_basic_stage(
        build_normal_stage(
            stage_of(table, "normal"),
            table,
            fixture.zone_table,
            fixture.character_table,
            fixture.building_data,
            fixture.item_table,
            fixture.level,
            {},
            stub_compile_rich_text,
        )
    )


def test_stage_rendering_matches_golden() -> None:
    fixture = load_fixture()
    stage_table = fixture.stage_table

    page = NormalPageView(
        normal=build_normal_stage(
            stage_of(stage_table, "normal"),
            stage_table,
            fixture.zone_table,
            fixture.character_table,
            fixture.building_data,
            fixture.item_table,
            fixture.level,
            {},
            stub_compile_rich_text,
            map_override="map_override",
        ),
        assault=build_4star_stage(
            stage_of(stage_table, "hard"),
            stage_table,
            fixture.zone_table,
            fixture.character_table,
            fixture.building_data,
            fixture.item_table,
            fixture.level,
            stub_compile_rich_text,
        ),
        enemies=build_enemies(
            fixture.level,
            fixture.enemy_table,
            fixture.enemy_levels,
            False,
        ),
        squads=build_squad_sections(
            fixture.level,
            "T-1 测试关卡",
            fixture.character_table,
            fixture.skill_table,
        ),
        material_drop=True,
    )
    actual = render_normal_page(page)
    expected = (
        (GOLDEN_DIR / "basic.wiki").read_text(encoding="utf-8").removesuffix("\n")
    )

    assert actual == expected


def test_zone_without_names_still_emits_the_parameter() -> None:
    """zone_table 里有 62 个区域两个名字字段都是 null。

    这些关卡的 |所属区域= 必须照旧输出字面量 None,而不能让整个参数消失 ——
    MediaWiki 模板对「参数缺失」和「参数为 None」的处理不同。
    """
    fixture = load_fixture()
    zone_table = ZoneTable.model_validate(
        {"zones": {"zone_1": {"zoneNameFirst": None, "zoneNameSecond": None}}}
    )
    raw_table = fixture.raw["stage_table"]
    raw_table["stages"]["normal"]["zoneId"] = "zone_1"
    raw_table["stages"]["hard"]["zoneId"] = "zone_1"
    stage_table = StageTable.model_validate(raw_table)

    normal = build_normal_stage(
        stage_of(stage_table, "normal"),
        stage_table,
        zone_table,
        fixture.character_table,
        fixture.building_data,
        fixture.item_table,
        fixture.level,
        {},
        stub_compile_rich_text,
    )
    assert normal.zone == "None"

    # 突袭关卡的 AssaultStageView.zone 声明为 str，None 会直接 ValidationError
    assault = build_4star_stage(
        stage_of(stage_table, "hard"),
        stage_table,
        zone_table,
        fixture.character_table,
        fixture.building_data,
        fixture.item_table,
        fixture.level,
        stub_compile_rich_text,
    )
    assert assault.zone == "None"

    rendered = render_normal_page(NormalPageView(normal=normal, assault=assault))
    assert rendered.count("|所属区域=None\n") == 2


def test_stage_table_tolerates_a_stage_with_missing_fields() -> None:
    """单个关卡的 schema 漂移不能让整张表校验失败,否则全部关卡都产不出来。"""
    fixture = load_fixture()
    stage_table = fixture.raw["stage_table"]
    del stage_table["stages"]["normal"]["dangerLevel"]

    table = StageTable.model_validate(stage_table)

    assert stage_of(table, "normal").danger_level is None
    assert stage_of(table, "hard").code == "T-1"


def test_stage_table_tolerates_a_null_drop_info() -> None:
    """stageDropInfo 为 null 的关卡按没有掉落处理,不能让整张表校验失败。"""
    fixture = load_fixture()

    rendered = normal_stage_with(fixture, stageDropInfo=None)

    assert "|首次掉落=" not in rendered
    assert "|常规掉落=" not in rendered
    assert "|额外物资=" not in rendered


def test_stage_table_keeps_null_for_optional_fields() -> None:
    """值为 null 的可选字段仍然是 None,不能被默认值悄悄改写成别的东西。"""
    fixture = load_fixture()
    stage_table = fixture.raw["stage_table"]
    stage_table["stages"]["normal"]["dangerLevel"] = None
    stage_table["stages"]["normal"]["levelId"] = None

    table = StageTable.model_validate(stage_table)

    assert stage_of(table, "normal").danger_level is None
    assert stage_of(table, "normal").level_id is None


def test_campaign_entry_template_renders_the_complete_page() -> None:
    progress = CampaignProgressView(
        rows=[
            CampaignProgressRowView(
                kill_count=100,
                items=[CampaignProgressItemView(name="龙门币", count=1000)],
                break_fee_add=25,
            )
        ]
    )
    page = CampaignPageView(
        stage=CampaignStageView(
            code="C-1",
            name="测试剿灭",
            stage_id="campaign_1",
            commission=False,
            stage_type="活动",
            difficulty="NORMAL",
            unlock_condition="—",
            zone="测试区域",
            description="测试描述",
            ap_cost=25,
        ),
        progress=progress,
    )

    assert render_campaign_page(page) == (
        "{{pathnav2|关卡一览}}\n"
        "==关卡==\n"
        "{{剿灭关卡信息\n"
        "|关卡代号=C-1\n"
        "|关卡名=测试剿灭\n"
        "|关卡id=campaign_1\n"
        "|关卡类型=活动\n"
        "|关卡难度=NORMAL\n"
        "|解锁条件=—\n"
        "|所属区域=测试区域\n"
        "|关卡描述=测试描述\n"
        "|作战消耗=25\n"
        "}}\n"
        "==作战进度奖励==\n"
        '{| class="wikitable mw-collapsible mw-collapsed" '
        'style="text-align:center;width:600px;"\n'
        '!style="width:200px;color:white;font-weight:bold;'
        'background-color:#575757;"|击溃人数\n'
        '!style="width:400px;color:white;font-weight:bold;'
        'background-color:#575757;"|奖励\n'
        "|-\n"
        "|100||{{材料消耗|龙门币|1000}} "
        "{{材料消耗|合成玉|i+}}(+25)\n"
        "|}\n"
        "==注释与链接==\n"
        "<references/>\n"
        "{{关卡导航}}"
    )


def test_empty_enemy_list_still_renders_the_section_when_level_exists() -> None:
    page = CampaignPageView(
        stage=CampaignStageView(
            code="C-1",
            name="测试剿灭",
            stage_id="campaign_1",
            commission=False,
            stage_type="活动",
            difficulty="NORMAL",
            unlock_condition="—",
            zone="测试区域",
            description="测试描述",
            ap_cost=25,
        ),
        enemies=[],
        progress=CampaignProgressView(rows=[]),
    )

    content = render_campaign_page(page)

    assert "==敌方情报==\n{{敌方情报\n}}" in content


# 以下用例对应 master 上旧字符串实现的行为,逐条与重构前的输出对拍确认过。
# 空值参数和缺失参数在 MediaWiki 里走不同分支,不能靠 add_optional 一把抹平。


@pytest.mark.parametrize(
    ("overrides", "expected_line"),
    [
        ({"description": None}, "|关卡描述=\n"),
        ({"description": ""}, "|关卡描述=\n"),
        ({"unlockCondition": []}, "|解锁条件=\n"),
        ({"unlockCondition": None}, "|解锁条件=\n"),
        ({"difficulty": ""}, "|关卡难度=\n"),
    ],
)
def test_empty_values_still_emit_the_parameter(
    overrides: dict, expected_line: str
) -> None:
    assert expected_line in normal_stage_with(load_fixture(), **overrides)


def test_assault_recommended_level_survives_an_empty_danger_level() -> None:
    fixture = load_fixture()
    raw_table = copy.deepcopy(fixture.raw["stage_table"])
    raw_table["stages"]["hard"]["dangerLevel"] = ""
    stage_table = StageTable.model_validate(raw_table)

    rendered = render_assault_stage(
        build_4star_stage(
            stage_of(stage_table, "hard"),
            stage_table,
            fixture.zone_table,
            fixture.character_table,
            fixture.building_data,
            fixture.item_table,
            fixture.level,
            stub_compile_rich_text,
        )
    )

    assert "|推荐等级=\n" in rendered


def test_battle_stage_marker_only_when_level_id_is_missing() -> None:
    """|战斗关卡=false 的判据是 levelId 缺失,空字符串不算。"""

    fixture = load_fixture()

    assert "|战斗关卡=false\n" in normal_stage_with(fixture, levelId=None)
    assert "|战斗关卡=" not in normal_stage_with(fixture, levelId="")


def test_pages_without_a_parameter_keep_it_absent() -> None:
    """生息演算关卡本来就没有难度/解锁条件/推荐等级,不能凭空补出来。"""

    fixture = load_fixture()
    stage = build_sandbox_v2_stage(
        SandboxV2StageData(
            code="SV-1",
            name="测试演算",
            stage_id="sandbox_1",
            level_id="Obt/Test/level_normal",
            description="描述",
            action_cost=3,
        ),
        stub_compile_rich_text,
        fixture.level,
        {},
    )
    rendered = render_basic_stage(stage)

    assert "|关卡难度=" not in rendered
    assert "|解锁条件=" not in rendered
    assert "|推荐等级=" not in rendered


def test_assault_comment_stays_tight_without_intelligence() -> None:
    """没有 ebuff 符文时注释里不留空行。"""

    fixture = load_fixture()
    raw_level = copy.deepcopy(fixture.raw["level_table"])
    raw_level["runes"] = []

    rendered = render_assault_stage(
        build_roguelike_4star_stage(
            RoguelikeGameStageData(code="RL-1", name="测试紧急", elite_desc="描述"),
            LevelData.model_validate(raw_level),
            stub_compile_rich_text,
        )
    )

    assert rendered.endswith("<!--|情报=\n-->\n}}")


def test_sandbox_page_keeps_its_table_of_contents() -> None:
    """生息演算页面历来不带 __NOTOC__,只有 crisis/memory/mechanism/id 带。"""

    page = BasicPageView(
        stage=BasicStageView(
            code="SV-1",
            name="测试演算",
            stage_id="sandbox_1",
            stage_type="生息演算",
        )
    )
    assert "__NOTOC__" not in render_basic_page(page)
    assert "__NOTOC__" in render_basic_page(page, notoc=True)


def test_squad_section_is_dropped_but_the_job_survives_broken_data() -> None:
    """单个干员数据缺字段只该丢掉这一关的固定编队,不能让异常冒泡。"""

    level = LevelData.model_validate(
        {
            "predefines": {
                "characterCards": [
                    {
                        "inst": {
                            "characterKey": "char_1",
                            "phase": "PHASE_2",
                            "level": 50,
                            "potentialRank": 0,
                            "favorPoint": 50,
                        },
                        "skillIndex": -1,
                        "mainSkillLvl": 7,
                    }
                ]
            }
        }
    )
    # 干员名为 null:模型里是 None,编队单位没法渲染,整节丢掉
    character_table = CharacterTable.validate_python(
        {"char_1": {"name": None, "skills": []}}
    )

    assert build_squad_sections(level, "T-1 测试关卡", character_table, {}) == []


def test_roguelike_page_matches_golden() -> None:
    """集成战略页面骨架:普通 + 紧急作战 + 敌方情报 + 分类。"""

    fixture = load_fixture()
    page = RoguelikePageView(
        normal=build_roguelike_stage(
            RoguelikeGameStageData(
                id="rogue_1",
                code="RL-1",
                name="测试关卡",
                level_id="Obt/Test/level_normal",
                description="第一行\\n第二行",
            ),
            fixture.level,
            {},
            stub_compile_rich_text,
        ),
        assault=build_roguelike_4star_stage(
            RoguelikeGameStageData(code="RL-1", name="测试关卡", elite_desc="紧急描述"),
            fixture.level,
            stub_compile_rich_text,
        ),
        enemies=build_enemies(
            fixture.level,
            fixture.enemy_table,
            fixture.enemy_levels,
            False,
        ),
    )

    expected = (
        (GOLDEN_DIR / "roguelike.wiki").read_text(encoding="utf-8").removesuffix("\n")
    )
    assert render_roguelike_page(page) == expected


def test_sandbox_page_matches_golden() -> None:
    """生息演算页面骨架:没有 __NOTOC__,带 tabber 特殊地图。"""

    fixture = load_fixture()
    page = BasicPageView(
        stage=build_sandbox_v2_stage(
            SandboxV2StageData(
                code="SV-1",
                name="测试演算",
                stage_id="sandbox_1",
                level_id="Obt/Test/level_normal",
                description="第一行\\n第二行",
                action_cost=3,
            ),
            stub_compile_rich_text,
            fixture.level,
            {},
        ),
        enemies=build_enemies(
            fixture.level,
            fixture.enemy_table,
            fixture.enemy_levels,
            False,
        ),
        squads=build_squad_sections(
            fixture.level,
            "SV-1 测试演算",
            fixture.character_table,
            fixture.skill_table,
        ),
    )

    expected = (
        (GOLDEN_DIR / "sandbox.wiki").read_text(encoding="utf-8").removesuffix("\n")
    )
    assert render_basic_page(page) == expected


def test_tile_effects_tolerate_a_level_without_tiles() -> None:
    """mapData 或 tiles 为 null 的关卡没有特殊地形,不能在这里炸掉。"""

    assert build_tile_effects(LevelData.model_validate({"mapData": None}), {}) == []
    assert (
        build_tile_effects(LevelData.model_validate({"mapData": {"tiles": None}}), {})
        == []
    )
