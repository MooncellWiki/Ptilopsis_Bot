import json
from pathlib import Path

from ptilopsis.gamedata.stage import StageTable
from ptilopsis.jobs.stage import (
    CampaignPageView,
    CampaignProgressItemView,
    CampaignProgressRowView,
    CampaignProgressView,
    CampaignStageView,
    NormalPageView,
    build_4star_stage,
    build_enemies,
    build_normal_stage,
    build_squad_sections,
    render_campaign_page,
    render_normal_page,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "stage"
GOLDEN_DIR = Path(__file__).parent / "golden" / "stage"


def stub_compile_rich_text(text: str) -> str:
    return f"[RTS]{text}"


def test_stage_rendering_matches_golden() -> None:
    fixture = json.loads((FIXTURE_DIR / "basic.json").read_text(encoding="utf-8"))
    level = fixture["level_table"]
    stage_table = fixture["stage_table"]

    page = NormalPageView(
        normal=build_normal_stage(
            stage_table["stages"]["normal"],
            stage_table,
            fixture["zone_table"],
            fixture["character_table"],
            fixture["building_data"],
            fixture["item_table"],
            level,
            {},
            stub_compile_rich_text,
            map_override="map_override",
        ),
        assault=build_4star_stage(
            stage_table["stages"]["hard"],
            stage_table,
            fixture["zone_table"],
            fixture["character_table"],
            fixture["building_data"],
            fixture["item_table"],
            level,
            stub_compile_rich_text,
        ),
        enemies=build_enemies(
            level,
            fixture["enemy_table"],
            fixture["enemy_database"],
            False,
        ),
        squads=build_squad_sections(
            level,
            "T-1 测试关卡",
            fixture["character_table"],
            fixture["skill_table"],
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
    fixture = json.loads((FIXTURE_DIR / "basic.json").read_text(encoding="utf-8"))
    zone_table = {"zones": {"zone_1": {"zoneNameFirst": None, "zoneNameSecond": None}}}
    stage_table = fixture["stage_table"]
    stage_table["stages"]["normal"]["zoneId"] = "zone_1"
    stage_table["stages"]["hard"]["zoneId"] = "zone_1"

    normal = build_normal_stage(
        stage_table["stages"]["normal"],
        stage_table,
        zone_table,
        fixture["character_table"],
        fixture["building_data"],
        fixture["item_table"],
        fixture["level_table"],
        {},
        stub_compile_rich_text,
    )
    assert normal.zone == "None"

    # 突袭关卡的 AssaultStageView.zone 声明为 str，None 会直接 ValidationError
    assault = build_4star_stage(
        stage_table["stages"]["hard"],
        stage_table,
        zone_table,
        fixture["character_table"],
        fixture["building_data"],
        fixture["item_table"],
        fixture["level_table"],
        stub_compile_rich_text,
    )
    assert assault.zone == "None"

    rendered = render_normal_page(NormalPageView(normal=normal, assault=assault))
    assert rendered.count("|所属区域=None\n") == 2


def test_stage_table_tolerates_a_stage_with_missing_fields() -> None:
    """单个关卡的 schema 漂移不能让整张表校验失败,否则全部关卡都产不出来。"""
    fixture = json.loads((FIXTURE_DIR / "basic.json").read_text(encoding="utf-8"))
    stage_table = fixture["stage_table"]
    del stage_table["stages"]["normal"]["dangerLevel"]

    table = StageTable.model_validate(stage_table)

    assert table.stages["normal"].danger_level is None
    assert table.stages["hard"].code == "T-1"


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
