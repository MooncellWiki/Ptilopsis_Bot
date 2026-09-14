from typing import Annotated

from ptilopsis.gamedata.building_data import BuildingData
from ptilopsis.gamedata.character_table import CharacterData
from ptilopsis.gamedata.item_table import InventoryData
from ptilopsis.gamedata.story_review_table import (
    ItemBundle,
    StoryReviewGroupClientData,
)
from ptilopsis.gamedata.zone_table import ZoneTable
from ptilopsis.jobs.params import (
    CharacterTable,
    ItemTable,
    StoryReviewTable,
    table,
)
from ptilopsis.log import logger
from ptilopsis.utils.data import GameData
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki


def parse_item(
    item: ItemBundle,
    character_table: dict[str, CharacterData],
    building_data: BuildingData,
    item_table: InventoryData,
) -> str:
    item_id = item.id or ""
    if item.type == "CHAR":
        return character_table[item_id].name or ""
    elif item.type == "FURN":
        custom_data = building_data.custom_data
        furnitures = (custom_data.furnitures if custom_data else None) or {}
        return furnitures[item_id].name or ""
    items = item_table.items or {}
    if item_id in items:
        return "{{{{材料消耗|{}|{}}}}}".format(
            (items[item_id].name or "").rstrip(), item.count
        )
    logger.info(f"Unknown reward item {item.id}.")
    return ""


async def update_story_review(
    gamedata: GameData,
    story_review_table: dict[str, StoryReviewGroupClientData],
    character_table: dict[str, CharacterData],
    building_data: BuildingData,
    item_table: InventoryData,
    zone_table: ZoneTable,
) -> str:
    content = "__TOC__\n"
    content_dict: dict[str, list[str]] = {
        "ACTIVITY_STORY": [],
        "MINI_STORY": [],
        "MAIN_STORY": [],
        "NONE": [],
    }
    activity_table_title = """{{{{锚点|{name}}}}}
{{| class="wikitable" style="position:relative; text-align:center; width:100%; max-width:1000px; display:table; font-size:14px;"
! colspan="2" style="text-align:center;"|<big><big>{name}</big></big>
|-
! class="nomobile"|[[文件:情报处理室 {name}.png|160px|link={name}]]
|<div style="clear:both; overflow:auto; width:100%; height:360px; background:transparent;">
{{|
"""
    mini_table_title = """{{{{锚点|{name}}}}}
{{| class="wikitable" style="position:relative; text-align:center; width:100%; max-width:1000px; display:table; font-size:14px;"
! colspan="2" style="text-align:center;"|<big><big>{name}</big></big>
|-
! class="nomobile"|[[文件:情报处理室 {name}.png|160px|link={name}]]
|<div style="clear:both; overflow:auto; width:100%; height:360px; background:transparent;">
{{|
"""
    main_table_title = """{{{{锚点|{name2}}}}}
{{| class="wikitable" style="position:relative; text-align:center; width:100%; max-width:1000px; display:table; font-size:14px;"
! colspan="2" style="text-align:center;"|<big><big>{name1}</big></big>
|-
! class="nomobile"|[[文件:章节名称 {name2}.png|160px|link=关卡一览#主线关卡一览]]
|<div style="clear:both; overflow:auto; width:100%; height:360px; background:transparent;">
{{|
"""
    zones = zone_table.zones or {}
    mainline_zone_ids = zone_table.mainline_zone_id_list or []
    # 剧情简介有两千多个小文件,先并发下载进缓存,下面的循环再逐个读
    await gamedata.prefetch(
        "story/[uc]" + story.story_info + ".txt"
        for group in story_review_table.values()
        for story in group.info_unlock_datas or []
        if story.story_info
    )
    for group in story_review_table.values():
        event_table = ""
        if group.act_type == "ACTIVITY_STORY":
            event_table += activity_table_title.format(name=group.name)
        elif group.act_type == "MINI_STORY":
            event_table += mini_table_title.format(name=group.name)
        elif group.act_type == "MAIN_STORY":
            # 老的主线 id 是 main_<序号>,按序号换成 zone_table 里的章节 id;
            # 换不到章节的(如尚未开放)直接跳过
            try:
                zone_id = group.id
                if zone_id is None or zone_id not in zones:
                    zone_id = mainline_zone_ids[int((zone_id or "")[5:])]
                    group.id = zone_id
                zone = zones[zone_id]
            except Exception:
                continue
            if zone.zone_name_first is None or zone.zone_name_second is None:
                continue
            event_table += main_table_title.format(
                name1=zone.zone_name_first + " " + zone.zone_name_second,
                name2=zone.zone_name_first,
            )
        elif group.act_type == "NONE":
            continue
        else:
            logger.info(f"Unknown actType {group.act_type} for {group.name}")
            continue

        story_list = []
        for story in group.info_unlock_datas or []:
            if story.story_info:
                path = "story/[uc]" + story.story_info + ".txt"
                try:
                    story_info = (
                        (await gamedata.get_txt(path, "CN"))
                        .rstrip()
                        .replace("\n", "<br/>")
                    )
                except Exception:
                    logger.info(f"路径名错误：{path}")
                    story_info = "{{color|red|剧情简介文件路径错误}}"
            else:
                story_info = ""
            story_list.append(
                f"{{{{剧情简介|{story.story_code}|{story.story_name}|{story.avg_tag}|{story_info}}}}}"
            )
        event_table += "\n|-\n".join(story_list) + "\n|}</div>"
        if group.rewards:
            event_table += "\n|-\n!解锁报酬\n|" + "".join(
                [
                    parse_item(item, character_table, building_data, item_table)
                    for item in group.rewards
                ]
            )
        event_table += "\n|}\n"
        content_dict[group.act_type].append(event_table)
    content += "==公共事务实录==\n" + "".join(content_dict["ACTIVITY_STORY"])
    content += "==特别行动记述==\n" + "".join(content_dict["MINI_STORY"])
    content += "==主线剧情==\n" + "".join(content_dict["MAIN_STORY"])

    return content


@job
async def run(
    wiki: Wiki,
    data: GameData,
    story_review_table: StoryReviewTable,
    character_table: CharacterTable,
    building_data: Annotated[BuildingData, table("building_data")],
    item_table: ItemTable,
    zone_table: Annotated[ZoneTable, table("zone_table")],
) -> None:
    content = await update_story_review(
        data,
        story_review_table,
        character_table,
        building_data,
        item_table,
        zone_table,
    )

    await wiki.edit(title="用户:Seniorious/情报处理室", text=content, summary="update")
    # logger.info(content)
    logger.info("Updated: {}.".format("用户:Seniorious/情报处理室"))
