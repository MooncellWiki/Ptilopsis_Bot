from ptilopsis.gamedata.building_data import BuildingData
from ptilopsis.gamedata.item_table import InventoryData
from ptilopsis.gamedata.stage_table import StageTable
from ptilopsis.jobs import params
from ptilopsis.jobs.basic import item_name
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki

# 页面上各 tab 的标题与对应的配方类型,按显示顺序
FORMULA_TABS = [
    ("基建材料", "F_BUILDING"),
    ("精英材料", "F_EVOLVE"),
    ("技巧概要", "F_SKILL"),
    ("芯片", "F_ASC"),
]


def stage_code(stage_table: StageTable, stage_id: str | None) -> str:
    """关卡代号(如 ``1-7``);关卡不存在时与旧代码一样抛 ``KeyError``。"""

    if stage_id is None or stage_table.stages is None:
        raise KeyError(stage_id)
    return stage_table.stages[stage_id].code or ""


def material(item_table: InventoryData, item_id: str | None, count: int) -> str:
    return f"{{{{材料消耗|{item_name(item_table, item_id).rstrip()}|{count}}}}}"


def get_workshop_formulas(
    building_data: BuildingData, item_table: InventoryData, stage_table: StageTable
) -> str:
    table_title = """{| class="wikitable logo" style="text-align:center; display:table; white-space:normal;"
|-
!解锁等级!!产品!!消耗材料!!消耗龙门币!!消耗心情!!副产品产出概率!!额外解锁条件"""
    text = "\n|-\n|{}||{}||{}||{}||{}||{}||{}"

    # {配方类型: {sortId: 行文本}},dict 保持配方表里的顺序
    formulas_content: dict[str, dict[int, str]] = {}
    for formula in (building_data.workshop_formulas or {}).values():
        require_level = "－"
        for room in formula.require_rooms or []:
            if room.room_id == "WORKSHOP":
                require_level = str(room.room_level)
        require_stage = ", ".join(
            f"{stage.rank}星通关[[{stage_code(stage_table, stage.stage_id)}]]"
            for stage in formula.require_stages or []
        )
        if require_stage == "":
            require_stage = "－"
        formula_content = text.format(
            require_level,
            material(item_table, formula.item_id, formula.count),
            " ".join(
                material(item_table, cost.id, cost.count)
                for cost in formula.costs or []
            ),
            formula.gold_cost,
            int(formula.ap_cost / 360000),
            f"{formula.extra_outcome_rate:.0%}",
            require_stage,
        )
        formulas_content.setdefault(formula.formula_type, {})[formula.sort_id] = (
            formula_content
        )

    tabs = [
        f"{title}=\n{table_title}{''.join(formulas_content[kind].values())}\n|}}"
        for title, kind in FORMULA_TABS
    ]
    return "<tabber>\n" + "\n|-|\n".join(tabs) + "\n</tabber>"


@job
def run(
    wiki: Wiki,
    building_data: params.BuildingData,
    item_table: params.ItemTable,
    stage_table: params.StageTable,
) -> None:
    content = get_workshop_formulas(building_data, item_table, stage_table)

    wiki.edit(title="用户:Seniorious/workshopFormulas", text=content, summary="update")
    # logger.info(content)
    logger.info("Updated: {}.".format("用户:Seniorious/workshopFormulas"))
