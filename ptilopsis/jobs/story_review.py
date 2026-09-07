from typing import Annotated, Any

from ptilopsis.jobs.params import (
    RawBuildingData,
    RawCharacterTable,
    RawItemTable,
    gamedata,
)
from ptilopsis.log import logger
from ptilopsis.utils.data import GameData
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki


def parse_item(item, character_table, building_data, item_table):
    if item["type"] == "CHAR":
        return character_table[item["id"]]["name"]
    elif item["type"] == "FURN":
        return building_data["customData"]["furnitures"][item["id"]]["name"]
    elif item["id"] in item_table["items"]:
        return "{{{{材料消耗|{}|{}}}}}".format(
            item_table["items"][item["id"]]["name"].rstrip(), item["count"]
        )
    else:
        logger.info("Unknown reward item {}.".format(item["id"]))


def update_story_review(
    gamedata, story_review_table, character_table, building_data, item_table, zone_table
):
    content = "__TOC__\n"
    content_dict = {
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
    memory_title = """{{{{锚点|{name2}}}}}
{{| class="wikitable" style="position:relative; text-align:center; width:100%; max-width:1000px; display:table; font-size:14px;"
! colspan="2" style="text-align:center;"|<big><big>{name1}</big></big>
|-
! class="nomobile"|[[文件:章节名称 {name2}.png|160px|link=关卡一览#主线关卡一览]]
|<div style="clear:both; overflow:auto; width:100%; height:360px; background:transparent;">
{{|
"""
    for event in story_review_table:
        event_table = ""
        if story_review_table[event]["actType"] == "ACTIVITY_STORY":
            event_table += activity_table_title.format(
                name=story_review_table[event]["name"]
            )
        elif story_review_table[event]["actType"] == "MINI_STORY":
            event_table += mini_table_title.format(
                name=story_review_table[event]["name"]
            )
        elif story_review_table[event]["actType"] == "MAIN_STORY":
            try:
                if story_review_table[event]["id"] not in zone_table["zones"]:
                    story_review_table[event]["id"] = zone_table["mainlineZoneIdList"][
                        int(story_review_table[event]["id"][5:])
                    ]
                event_table += main_table_title.format(
                    name1=zone_table["zones"][story_review_table[event]["id"]][
                        "zoneNameFirst"
                    ]
                    + " "
                    + zone_table["zones"][story_review_table[event]["id"]][
                        "zoneNameSecond"
                    ],
                    name2=zone_table["zones"][story_review_table[event]["id"]][
                        "zoneNameFirst"
                    ],
                )
            except:
                continue
        elif story_review_table[event]["actType"] == "NONE":
            continue
        else:
            logger.info(
                "Unknown actType {} for {}".format(
                    story_review_table[event]["actType"],
                    story_review_table[event]["name"],
                )
            )
            continue

        story_list = []
        for story in story_review_table[event]["infoUnlockDatas"]:
            if story["storyInfo"]:
                try:
                    story_info = (
                        gamedata.get_txt(
                            "story/[uc]" + story["storyInfo"] + ".txt", "CN"
                        )
                        .rstrip()
                        .replace("\n", "<br/>")
                    )
                except:
                    logger.info(
                        "路径名错误：", "story/[uc]" + story["storyInfo"] + ".txt"
                    )
                    story_info = "{{color|red|剧情简介文件路径错误}}"
            else:
                story_info = ""
            story_list.append(
                "{{{{剧情简介|{}|{}|{}|{}}}}}".format(
                    story["storyCode"], story["storyName"], story["avgTag"], story_info
                )
            )
        event_table += "\n|-\n".join(story_list) + "\n|}</div>"
        if story_review_table[event]["rewards"]:
            event_table += "\n|-\n!解锁报酬\n|" + "".join(
                [
                    parse_item(item, character_table, building_data, item_table)
                    for item in story_review_table[event]["rewards"]
                ]
            )
        event_table += "\n|}\n"
        content_dict[story_review_table[event]["actType"]].append(event_table)
    content += "==公共事务实录==\n" + "".join(content_dict["ACTIVITY_STORY"])
    content += "==特别行动记述==\n" + "".join(content_dict["MINI_STORY"])
    content += "==主线剧情==\n" + "".join(content_dict["MAIN_STORY"])

    return content


@job
def run(
    wiki: Wiki,
    data: GameData,
    story_review_table: Annotated[
        dict[str, Any], gamedata("excel/story_review_table.json")
    ],
    character_table: RawCharacterTable,
    building_data: RawBuildingData,
    item_table: RawItemTable,
    zone_table: Annotated[dict[str, Any], gamedata("excel/zone_table.json")],
) -> None:
    content = update_story_review(
        data,
        story_review_table,
        character_table,
        building_data,
        item_table,
        zone_table,
    )

    wiki.edit(title="用户:Seniorious/情报处理室", text=content, summary="update")
    # logger.info(content)
    logger.info("Updated: {}.".format("用户:Seniorious/情报处理室"))
