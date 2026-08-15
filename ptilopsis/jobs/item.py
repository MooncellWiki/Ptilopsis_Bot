from collections.abc import Collection

from pydantic import BaseModel

from ptilopsis.gamedata.building import (
    BuildingData,
    BuildingDataManufactFormula,
    BuildingDataWorkshopFormula,
)
from ptilopsis.gamedata.item import (
    InventoryData,
    ItemData,
    ItemRarity,
)
from ptilopsis.gamedata.stage import StageTable
from ptilopsis.log import logger
from ptilopsis.utils.job import JobContext, job
from ptilopsis.wikitext import WikiTemplate

# 渲染视图,字段与页面上的 wiki 模板参数一一对应


class IngredientView(BaseModel):
    name: str
    count: int


class ByproductView(BaseModel):
    name: str
    drop_rate: float


class StageRequirementView(BaseModel):
    rank: int
    code: str
    name: str


class ManufactureFormulaView(BaseModel):
    product_name: str
    count: int
    weight: int
    cost_time: str
    room_level: int
    ingredients: list[IngredientView]


class WorkshopFormulaView(BaseModel):
    product_name: str
    count: int
    gold_cost: int
    ap_cost: float
    room_level: int
    extra_outcome_rate: float
    ingredients: list[IngredientView]
    byproducts: list[ByproductView]
    stage_requirement: StageRequirementView | None


class ItemPageView(BaseModel):
    name: str
    item_id: str
    icon_id: str
    description: str
    usage: str
    obtain_approach: str
    rarity: int | str
    sort_id: int
    category: str
    manufacture_formulas: list[ManufactureFormulaView]
    workshop_formulas: list[WorkshopFormulaView]
    # 即使 buildingProductList 里只有未知房间类型(两类配方都渲染不出来),
    # 旧实现也会输出"==材料掉落=="标题
    has_building_products: bool


EXCLUDED_ITEM_IDS = frozenset(
    {
        "act13side_prestige_armorless",
        "LINKAGE_TKT_GACHA_10_1701",
        "LINKAGE_TKT_GACHA_10_4801",
    }
)


def build_time(seconds: int) -> str:
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def resolve_rarity(rarity: str) -> int | str:
    # 未知的稀有度成员名原样传给 wiki,等页面模板跟进新枚举
    if rarity in ItemRarity.__members__:
        return ItemRarity[rarity].value
    return rarity


def classify_item(item_key: str, name: str) -> str:
    # 信物/芯片类靠名字里有没有对应字样区分,顺序不可调换:
    # "的中坚信物"包含"信物"但不含"的信物",先判窄的再判宽的
    if "的信物" in name:
        return "信物"
    if "的中坚信物" in name:
        return "中坚信物"
    if "信物" in name:
        return "通用信物"
    if name.find("芯片组") > 0:
        return "芯片组"
    if name.find("双芯片") > 0:
        return "双芯片"
    if name.find("芯片") > 0:
        return "芯片"
    # 纯数字 itemId 达到五位(>= 10000)即为材料,无法解析的是活动等临时道具
    try:
        return "材料" if int(item_key) / 10000 >= 1 else "其他道具"
    except ValueError:
        return "其他道具"


def should_skip_item(
    item: ItemData,
    existing_items: Collection[str],
    unimplemented_items: Collection[str],
) -> bool:
    name = item.name.strip()
    if name in unimplemented_items or name in existing_items:
        return True
    if item.hide_in_item_get:
        return True
    if item.item_id.endswith("bossrush_relic_04"):
        return True
    if (
        item.item_id.startswith("act1vhalfidle_")
        and item.item_id != "act1vhalfidle_token_point"
    ):
        return True
    if item.item_id in EXCLUDED_ITEM_IDS:
        return True
    return item.item_type == "EMOTICON_SET"


def build_recipe_approach(item: ItemData) -> str:
    # 获得方式 = 数据里的 obtainApproach 加上可制造的设施名,去重并保持出现顺序
    approaches = []
    for product in item.building_product_list:
        approach = {
            "MANUFACTURE": "制造站",
            "WORKSHOP": "加工站",
        }.get(product.room_type)
        if approach is not None and approach not in approaches:
            approaches.append(approach)

    obtain_approach = item.obtain_approach or ""
    if approaches:
        recipe_approach = "、".join(approaches)
        if obtain_approach:
            return f"{obtain_approach}、{recipe_approach}"
        return recipe_approach
    return obtain_approach


def build_manufacture_formula(
    formula: BuildingDataManufactFormula, item_table: InventoryData
) -> ManufactureFormulaView:
    ingredients = [
        IngredientView(
            name=item_table.items[cost.id].name.rstrip(),
            count=cost.count,
        )
        for cost in formula.costs
    ]
    return ManufactureFormulaView(
        product_name=item_table.items[formula.item_id].name.rstrip(),
        count=formula.count,
        weight=formula.weight,
        cost_time=build_time(formula.cost_point),
        room_level=formula.require_rooms[0].room_level,
        ingredients=ingredients,
    )


def build_workshop_formula(
    formula: BuildingDataWorkshopFormula,
    item_table: InventoryData,
    stage_table: StageTable,
) -> WorkshopFormulaView:
    ingredients = [
        IngredientView(
            name=item_table.items[cost.id].name.rstrip(),
            count=cost.count,
        )
        for cost in formula.costs
    ]

    # 副产物掉率按组内权重占比折算成百分数,保留一位小数
    total_weight = sum(outcome.weight for outcome in formula.extra_outcome_group)
    byproducts = [
        ByproductView(
            name=item_table.items[outcome.item_id].name.rstrip(),
            drop_rate=round(outcome.weight / total_weight * 100, 1),
        )
        for outcome in formula.extra_outcome_group
    ]

    stage_requirement = None
    if formula.require_stages:
        requirement = formula.require_stages[0]
        stage = stage_table.stages[requirement.stage_id]
        code = stage.code
        name = stage.name
        if code is None or name is None:
            raise ValueError(
                f"Stage {requirement.stage_id} used by a workshop formula "
                "has no display code or name."
            )
        stage_requirement = StageRequirementView(
            rank=requirement.rank,
            code=code,
            name=name,
        )

    return WorkshopFormulaView(
        product_name=item_table.items[formula.item_id].name.rstrip(),
        count=formula.count,
        gold_cost=formula.gold_cost,
        # apCost 的单位是毫秒,页面上按 1 心情 = 360000ms 折算
        ap_cost=formula.ap_cost / 360000,
        room_level=formula.require_rooms[0].room_level,
        extra_outcome_rate=formula.extra_outcome_rate * 100,
        ingredients=ingredients,
        byproducts=byproducts,
        stage_requirement=stage_requirement,
    )


def build_item(
    item_key: str,
    item: ItemData,
    item_table: InventoryData,
    building_data: BuildingData,
    stage_table: StageTable,
) -> ItemPageView:
    manufacture_formulas = []
    workshop_formulas = []
    for product in item.building_product_list:
        if product.room_type == "MANUFACTURE":
            formula = building_data.manufact_formulas[product.formula_id]
            manufacture_formulas.append(build_manufacture_formula(formula, item_table))
        elif product.room_type == "WORKSHOP":
            formula = building_data.workshop_formulas[product.formula_id]
            workshop_formulas.append(
                build_workshop_formula(formula, item_table, stage_table)
            )
        else:
            logger.info(f"Unknown building room type {product.room_type}.")

    return ItemPageView(
        name=item.name.strip(),
        item_id=item.item_id,
        icon_id=item.icon_id or "",
        description=item.description or "",
        usage=item.usage or "",
        obtain_approach=build_recipe_approach(item),
        rarity=resolve_rarity(item.rarity),
        sort_id=item.sort_id,
        category=classify_item(item_key, item.name),
        manufacture_formulas=manufacture_formulas,
        workshop_formulas=workshop_formulas,
        has_building_products=bool(item.building_product_list),
    )


def render_basic_info(item: ItemPageView) -> str:
    template = WikiTemplate("道具信息")
    template.add("名称", item.name)
    template.add("itemId", item.item_id)
    template.add("iconId", item.icon_id)
    template.add("描述", item.description)
    template.add("用途", item.usage)
    template.add_optional("获得方式", item.obtain_approach)
    template.add("稀有度", item.rarity)
    template.add("id", item.sort_id)
    template.add("分类", item.category)
    return f"==基础信息==\n{template}\n"


def render_manufacture_formula(formula: ManufactureFormulaView) -> str:
    template = WikiTemplate("道具配方/制造站")
    template.add("产物", formula.product_name)
    template.add("产物数量", formula.count)
    template.add("仓库消耗", formula.weight)
    template.add("时间消耗", formula.cost_time)
    template.add("制造站等级需求", formula.room_level)
    # 原料参数键名带序号,制造站模板的编号从 0 开始(加工站从 1 开始),
    # 两套编号都是 wiki 侧的历史约定
    for index, ingredient in enumerate(formula.ingredients):
        template.add(f"原料{index}", ingredient.name)
        template.add(f"原料{index}数量", ingredient.count)
    return str(template)


def render_workshop_formula(formula: WorkshopFormulaView) -> str:
    template = WikiTemplate("道具配方/加工站")
    template.add("产物", formula.product_name)
    template.add("产物数量", formula.count)
    template.add("龙门币消耗", formula.gold_cost)
    template.add("心情消耗", f"{formula.ap_cost:.0f}")
    template.add("加工站等级需求", formula.room_level)
    template.add("副产物总概率", f"{formula.extra_outcome_rate:.0f}")
    if formula.stage_requirement is not None:
        template.add("通关评价", formula.stage_requirement.rank)
        template.add("关卡", formula.stage_requirement.code)
        template.add("通关条件", formula.stage_requirement.name)
    for index, ingredient in enumerate(formula.ingredients, 1):
        template.add(f"原料{index}", ingredient.name)
        template.add(f"原料{index}数量", ingredient.count)
    for index, byproduct in enumerate(formula.byproducts, 1):
        template.add(f"副产物{index}", byproduct.name)
        template.add(f"副产物{index}掉率", byproduct.drop_rate)
    return str(template)


def render_manufacture_section(formulas: list[ManufactureFormulaView]) -> str:
    # 同类多条配方沿用旧实现的首尾相接格式,之间不插入换行
    return "==制造站==\n" + "".join(
        render_manufacture_formula(formula) for formula in formulas
    )


def render_workshop_section(formulas: list[WorkshopFormulaView]) -> str:
    return "==加工站==\n" + "".join(
        render_workshop_formula(formula) for formula in formulas
    )


def render_item(item: ItemPageView) -> str:
    # 各段的衔接沿袭旧实现的逐字节拼接:基础信息段以换行结尾、制造站分区
    # 末尾补一个换行、加工站分区与"材料掉落"标题之间没有换行;没有配方
    # 分区时留出一个空行
    blocks = ["{{Navigator|道具一览}}\n", render_basic_info(item)]
    if item.manufacture_formulas:
        blocks.append(render_manufacture_section(item.manufacture_formulas) + "\n")
    if item.workshop_formulas:
        blocks.append(render_workshop_section(item.workshop_formulas))
    if item.has_building_products:
        blocks.append("==材料掉落==")
    blocks.append("\n{{道具导航}}")
    return "".join(blocks)


def update_item(
    item_key: str,
    item_table: dict,
    building_data: dict,
    stage_table: dict,
) -> str:
    items = InventoryData.model_validate(item_table)
    building = BuildingData.model_validate(building_data)
    stages = StageTable.model_validate(stage_table)
    view = build_item(item_key, items.items[item_key], items, building, stages)
    return render_item(view)


@job
def run(ctx: JobContext) -> None:
    stage_table = StageTable.model_validate(ctx.getgd("excel/stage_table.json"))
    item_table = InventoryData.model_validate(ctx.getgd("excel/item_table.json"))
    building_data = BuildingData.model_validate(ctx.getgd("excel/building_data.json"))
    existing_items = ctx.wiki.category("分类:道具")
    unimplemented_items = ctx.wiki.category("分类:未实装道具")

    for item_key, item in item_table.items.items():
        if should_skip_item(item, existing_items, unimplemented_items):
            continue

        view = build_item(item_key, item, item_table, building_data, stage_table)
        try:
            ctx.wiki.edit(
                title=item.name.rstrip(),
                text=render_item(view),
                summary="item init",
                createonly=True,
            )
        except Exception:
            logger.info(f"Fail editing page: {item.name}")
