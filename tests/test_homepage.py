from ptilopsis.gamedata.activity_table import ActivityTable
from ptilopsis.gamedata.stage_table import StageData
from ptilopsis.gamedata.zone_table import ZoneTable
from ptilopsis.homepage import (
    code_prefixes,
    furniture_card,
    render_new_stages,
    render_stage_block,
    render_stage_list,
)

# 结构取自 26-09-22 的国服 gamedata:
# 矢量突破#3 三个区域、逐影集趣两个区域、保全派驻没有名字
ZONES = ZoneTable.model_validate(
    {
        "zones": {
            "act3break_zone1": {
                "zoneID": "act3break_zone1",
                "zoneNameSecond": "核心突破",
            },
            "act3break_zone2": {
                "zoneID": "act3break_zone2",
                "zoneNameSecond": "全力以赴",
            },
            "act1dp_zone1": {"zoneID": "act1dp_zone1", "zoneNameSecond": "轻游"},
            "weekly_1": {"zoneID": "weekly_1", "zoneNameSecond": "固若金汤"},
            "tower_n_21": {"zoneID": "tower_n_21"},
        }
    }
)
ACTIVITIES = ActivityTable.model_validate(
    {
        "zoneToActivity": {
            "act3break_zone1": "act3break",
            "act3break_zone2": "act3break",
            "act1dp_zone1": "act1dp",
        },
        "basicInfo": {
            "act3break": {"id": "act3break", "name": "矢量突破#3 拟生态"},
            "act1dp": {"id": "act1dp", "name": "逐影集趣"},
        },
    }
)


def stage(code: str, zone_id: str, stage_type: str = "ACTIVITY") -> StageData:
    return StageData.model_validate(
        {"code": code, "zoneId": zone_id, "stageType": stage_type}
    )


def test_code_prefixes_dedupes_in_order() -> None:
    assert code_prefixes(["DP-1", "DS-1", "DP-EX-1", ""]) == "DP · DS"


def test_stage_block_writes_each_stage_as_a_call() -> None:
    # 页面名里的半角逗号原样保留,不当分隔符
    assert render_stage_block("主线", [("", ["6-13 没有火,没有光"])], en="6") == (
        "{{首页/新增关卡\n|1=主线\n|en=6\n|2=\n"
        "|3={{首页/新增关卡/关卡|6-13 没有火,没有光}}\n}}"
    )


def test_stage_block_splits_beyond_max_groups() -> None:
    groups = [(f"组{i}", [f"X-{i} 关"]) for i in range(8)]
    text = render_stage_block("活动", groups)
    assert text.count("{{首页/新增关卡\n|1=活动") == 2
    assert "|2=组6\n" in text.split("\n}}\n")[1]


def test_new_stages_group_by_activity_then_zone() -> None:
    text = render_new_stages(
        [
            (stage("VEC-01", "act3break_zone1"), "VEC-01 寂静螺旋"),
            (stage("VEC-02", "act3break_zone1"), "VEC-02 波形扭曲"),
            (stage("VEC-A", "act3break_zone2"), "VEC-A 卓绝之巅"),
            (stage("DP-1", "act1dp_zone1"), "DP-1 入场吧绒绒！"),
        ],
        ZONES,
        ACTIVITIES,
    )
    assert text == (
        "{{首页/新增关卡\n|1=矢量突破#3 拟生态\n|en=VEC\n"
        "|2=核心突破\n"
        "|3={{首页/新增关卡/关卡|VEC-01 寂静螺旋}}"
        "{{首页/新增关卡/关卡|VEC-02 波形扭曲}}\n"
        "|4=全力以赴\n"
        "|5={{首页/新增关卡/关卡|VEC-A 卓绝之巅}}\n}}\n"
        "{{首页/新增关卡\n|1=逐影集趣\n|en=DP\n"
        "|2=轻游\n|3={{首页/新增关卡/关卡|DP-1 入场吧绒绒！}}\n}}"
    )


def test_new_stages_without_activity_use_zone_or_type_name() -> None:
    text = render_new_stages(
        [
            (stage("LS-6", "weekly_1", "DAILY"), "LS-6 固若金汤"),
            (stage("LT-1", "tower_n_21", "CLIMB_TOWER"), "LT-1 铁锈闸口"),
        ],
        ZONES,
        ACTIVITIES,
    )
    # 区域名已经当了标题,不再重复成分组名
    assert "|1=固若金汤\n|en=LS\n|2=\n" in text
    assert "|1=保全派驻\n|en=LT\n|2=\n" in text


def test_stage_list_is_one_ungrouped_block() -> None:
    assert render_stage_list("悖论模拟", [("", "悖论模拟 逻各斯")]) == (
        "{{首页/新增关卡\n|1=悖论模拟\n|2=\n"
        "|3={{首页/新增关卡/关卡|悖论模拟 逻各斯}}\n}}"
    )


def test_furniture_card() -> None:
    assert furniture_card("饰牌《清甜》") == "{{首页/家具卡|1=饰牌《清甜》}}"
    assert (
        furniture_card("黑流印象", theme=True) == "{{首页/家具卡|1=黑流印象|theme=1}}"
    )
