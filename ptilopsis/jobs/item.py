from typing import Annotated

from ptilopsis.gamedata.building_data import BuildingData
from ptilopsis.gamedata.item_table import ItemData
from ptilopsis.jobs.params import ItemTable, StageTable, category, table
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki


def item_name(items: dict[str, ItemData], item_id: str | None) -> str:
    """道具名(去掉尾随空白;个别老道具名带空格)。"""

    return (items[item_id or ""].name or "").rstrip()


def build_time(sec):
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    return "%02d:%02d:%02d" % (h, m, s)


def trans_rarity(rarity):
    return {
        "TIER_1": 0,
        "TIER_2": 1,
        "TIER_3": 2,
        "TIER_4": 3,
        "TIER_5": 4,
        "TIER_6": 5,
    }.get(rarity, rarity)


basic_info4 = (
    "==基础信息==\n{{{{道具信息\n|名称={name}\n|itemId={itemId}\n|iconId={iconId}\n|描述={description}\n|用途={usage}\n|"
    "获得方式={obtainApproach}\n|稀有度={rarity}\n|id={id}\n|分类={sort}\n}}}}\n"
)
basic_info3 = (
    "==基础信息==\n{{{{道具信息\n|名称={name}\n|itemId={itemId}\n|iconId={iconId}\n|描述={description}\n|用途={usage}\n|"
    "稀有度={rarity}\n|id={id}\n|分类={sort}\n}}}}\n"
)
basic_mf = (
    "{{{{道具配方/制造站\n|产物={name}\n|产物数量={count}\n|仓库消耗={weight}\n|"
    "时间消耗={costPoint}\n|制造站等级需求={roomLevel}\n"
)
basic_wf = (
    "{{{{道具配方/加工站\n|产物={name}\n|产物数量={count}\n|龙门币消耗={goldCost}\n|"
    "心情消耗={apCost:.0f}\n|加工站等级需求={roomLevel}\n|副产物总概率={extraOutcomeRate:.0f}\n"
)


@job
async def run(
    wiki: Wiki,
    stage_table: StageTable,
    item_table: ItemTable,
    building_data: Annotated[BuildingData, table("building_data")],
    item_pages: Annotated[list[str], category("分类:道具")],
    unreleased_pages: Annotated[list[str], category("分类:未实装道具")],
) -> None:
    items = item_table.items or {}
    stages = stage_table.stages or {}
    manufact_formulas = building_data.manufact_formulas or {}
    workshop_formulas = building_data.workshop_formulas or {}
    for item, citem in items.items():
        name = citem.name or ""
        item_id = citem.item_id or ""
        if name.strip() in unreleased_pages:
            continue
        if name.strip() in item_pages:
            continue
        if citem.hide_in_item_get:
            continue
        if item_id.endswith("bossrush_relic_04"):
            continue
        if (
            item_id.startswith("act1vhalfidle_")
            and item_id != "act1vhalfidle_token_point"
        ):
            continue
        if item_id in [
            "act13side_prestige_armorless",
            "LINKAGE_TKT_GACHA_10_1701",
            "LINKAGE_TKT_GACHA_10_4801",
        ]:
            continue
        if citem.item_type == "EMOTICON_SET":
            continue
        if name.find("的信物") != -1:
            sort = "信物"
        elif name.find("的中坚信物") != -1:
            sort = "中坚信物"
        elif name.find("信物") != -1:
            sort = "通用信物"
        elif name.find("芯片组") > 0:
            sort = "芯片组"
        elif name.find("双芯片") > 0:
            sort = "双芯片"
        elif name.find("芯片") > 0:
            sort = "芯片"
        else:
            try:
                if int(item) / 10000 >= 1:
                    sort = "材料"
                else:
                    sort = "其他道具"
                if int(item) == 73:
                    logger.info("")
            except Exception:
                sort = "其他道具"
        # 收集制造站/加工站配方信息
        recipe_approaches = []
        if citem.building_product_list:
            for d in citem.building_product_list:
                room_type = d.room_type
                if room_type == "MANUFACTURE":
                    recipe_approaches.append("制造站")
                elif room_type == "WORKSHOP":
                    recipe_approaches.append("加工站")
            # 去重保持顺序
            seen = set()
            unique_approaches = []
            for a in recipe_approaches:
                if a not in seen:
                    seen.add(a)
                    unique_approaches.append(a)
            recipe_approaches = unique_approaches

        original_obtain = citem.obtain_approach or ""
        if recipe_approaches:
            recipe_str = "、".join(recipe_approaches)
            if original_obtain:
                obtainApproach = original_obtain + "、" + recipe_str
            else:
                obtainApproach = recipe_str
        else:
            obtainApproach = original_obtain

        if obtainApproach:
            tbasic_info = basic_info4.format(
                name=name.strip(),
                itemId=citem.item_id,
                iconId=citem.icon_id if citem.icon_id is not None else "",
                description=citem.description if citem.description is not None else "",
                usage=citem.usage if citem.usage is not None else "",
                obtainApproach=obtainApproach,
                rarity=trans_rarity(citem.rarity),
                id=citem.sort_id,
                sort=sort,
            )
        else:
            tbasic_info = basic_info3.format(
                name=name.strip(),
                itemId=citem.item_id,
                iconId=citem.icon_id if citem.icon_id is not None else "",
                description=citem.description if citem.description is not None else "",
                usage=citem.usage if citem.usage is not None else "",
                rarity=trans_rarity(citem.rarity),
                id=citem.sort_id,
                sort=sort,
            )
        if citem.building_product_list:
            tmf = ""
            twf = ""
            for d in citem.building_product_list:
                cRoomType = d.room_type
                cFormulaId = d.formula_id or ""
                if cRoomType == "MANUFACTURE":
                    cf = manufact_formulas[cFormulaId]
                    tmf += basic_mf.format(
                        name=item_name(items, cf.item_id),
                        count=cf.count,
                        weight=cf.weight,
                        costPoint=build_time(cf.cost_point),
                        roomLevel=(cf.require_rooms or [])[0].room_level,
                    )
                    tstr = ""
                    for i, cost in enumerate(cf.costs or []):
                        tstr = (
                            tstr
                            + "|原料"
                            + str(i)
                            + "="
                            + item_name(items, cost.id)
                            + "\n|原料"
                            + str(i)
                            + "数量="
                            + str(cost.count)
                            + "\n"
                        )
                    tmf = tmf + tstr
                    tmf = tmf + "}}"
                elif cRoomType == "WORKSHOP":
                    cf = workshop_formulas[cFormulaId]
                    twf += basic_wf.format(
                        name=item_name(items, cf.item_id),
                        count=cf.count,
                        goldCost=cf.gold_cost,
                        apCost=cf.ap_cost / 360000,
                        roomLevel=(cf.require_rooms or [])[0].room_level,
                        extraOutcomeRate=cf.extra_outcome_rate * 100,
                    )
                    tstr = ""
                    for i, cost in enumerate(cf.costs or []):
                        tstr = (
                            tstr
                            + "|原料"
                            + str(i + 1)
                            + "="
                            + item_name(items, cost.id)
                            + "\n|原料"
                            + str(i + 1)
                            + "数量="
                            + str(cost.count)
                            + "\n"
                        )
                    extra_outcome_group = cf.extra_outcome_group or []
                    totalWeight = 0
                    for oc in extra_outcome_group:
                        totalWeight += oc.weight
                    for i, oc in enumerate(extra_outcome_group):
                        tstr = (
                            tstr
                            + "|副产物"
                            + str(i + 1)
                            + "="
                            + item_name(items, oc.item_id)
                            + "\n|副产物"
                            + str(i + 1)
                            + "掉率="
                            + str(round(oc.weight / totalWeight * 100, 1))
                            + "\n"
                        )
                    if cf.require_stages:
                        require_stage = cf.require_stages[0]
                        stage = stages[require_stage.stage_id or ""]
                        twf = (
                            twf
                            + "|通关评价="
                            + str(require_stage.rank)
                            + "\n|关卡="
                            + (stage.code or "")
                            + "\n|通关条件="
                            + (stage.name or "")
                            + "\n"
                        )
                    twf = twf + tstr + "}}"
                else:
                    logger.info("error")
            if tmf:
                tbasic_info = tbasic_info + "==制造站==\n" + tmf + "\n"
            if twf:
                tbasic_info = tbasic_info + "==加工站==\n" + twf
            if sort:
                tbasic_info = tbasic_info + "==材料掉落=="
            # 更新副产物
            # if twf:
            #     old = wiki.read(citem['name'].rstrip())
            #     result = re.search(r"==加工站==\n([\s\S]*?)\n+==", old)
            #     if result:
            #         new = old.replace(result.group(1), twf)
            #     else:
            #         new = old
            #     if new != old and citem['name'] != '家具零件':
            #         # logger.info(new)
            #         wiki.edit(title=citem['name'].rstrip(), text=new)
            #         logger.info("edit", citem['name'].rstrip())
            #     else:
            #         logger.info(citem['name'].rstrip(), 'same')
        fin = "{{Navigator|道具一览}}\n" + tbasic_info + "\n{{道具导航}}"
        # logger.info(fin)
        try:
            await wiki.edit(
                title=name.rstrip(),
                text=fin,
                summary="item init",
                createonly=True,
            )
        except Exception:
            logger.info(f"Fail editing Page: {name}")
