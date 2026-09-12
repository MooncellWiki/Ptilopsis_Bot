from datetime import datetime
from typing import Annotated

import pytz

from ptilopsis.gamedata.activity_table import (
    ActivityTable,
    ItemBundle,
    MissionDisplayRewards,
)
from ptilopsis.gamedata.building_data import BuildingData
from ptilopsis.gamedata.character_table import CharacterData
from ptilopsis.gamedata.item_table import InventoryData
from ptilopsis.gamedata.skin_table import CharSkinData, SkinTable
from ptilopsis.jobs.params import CharacterTable, ItemTable, RichText, table
from ptilopsis.log import logger
from ptilopsis.utils import richtext
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki

table_title = '{|class = "wikitable mw-collapsible mw-collapsed" style = "text-align:center; display:table; white-space:normal; width:800px;"'


def format_time(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, pytz.timezone("Asia/Shanghai")).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def skin_order(skin: CharSkinData) -> int:
    display = skin.display_skin
    return display.on_year * 12 + display.on_period if display else 0


def parse_item(
    item_type: str,
    item_id: str,
    item_count: int,
    item_table: InventoryData,
    building_data: BuildingData,
    character_table: dict[str, CharacterData],
    skin_table: SkinTable,
    skin_count_default: int,
) -> str:
    """奖励 / 兑换物按类型渲染成对应模板。

    皮肤按同一干员皮肤的上线时间排序后取序号;找不到时用 ``skin_count_default``
    (奖励里是 0,兑换物里是 -1,沿用旧页面)。
    """

    if item_type == "FURN":
        custom_data = building_data.custom_data
        furnitures = (custom_data.furnitures if custom_data else None) or {}
        return f"{{{{关卡报酬|家具=yes|{furnitures[item_id].name}||50}}}}"
    elif item_type == "CHAR":
        return f"{{{{招聘合同|{character_table[item_id].name}|50}}}}"
    elif item_type == "CHAR_SKIN":
        char_skins = skin_table.char_skins or {}
        skin_count = skin_count_default
        char_id = char_skins[item_id].char_id or ""
        char_key = char_id + "@"
        skin_list = [
            char_skins[skin_id] for skin_id in char_skins if char_key in skin_id
        ]
        skin_list.sort(key=skin_order)
        for index, skin_data in enumerate(skin_list):
            if skin_data.skin_id == item_id:
                skin_count = index + 1
        return f"{{{{皮肤头像|{character_table[char_id].name}|50|{skin_count}}}}}"
    else:
        items = item_table.items or {}
        return "{{{{材料消耗|{name}|{count}|50}}}}".format(
            name=(items[item_id].name or "").strip() if item_id in items else item_id,
            count=item_count,
        )


def parse_reward(
    reward: ItemBundle | MissionDisplayRewards,
    item_table: InventoryData,
    building_data: BuildingData,
    character_table: dict[str, CharacterData],
    skin_table: SkinTable,
) -> str:
    return parse_item(
        reward.type,
        reward.id or "",
        reward.count,
        item_table,
        building_data,
        character_table,
        skin_table,
        skin_count_default=0,
    )


def update_activity(
    activity_table: ActivityTable,
    item_table: InventoryData,
    building_data: BuildingData,
    character_table: dict[str, CharacterData],
    skin_table: SkinTable,
    rts: richtext.RichText,
) -> str:
    items = item_table.items or {}
    basic_info = activity_table.basic_info or {}
    detail = activity_table.activity
    collection_acts = (detail.collection if detail else None) or {}
    checkin_acts = (detail.checkin_only if detail else None) or {}
    act4d0_acts = (detail.type_act4_d0 if detail else None) or {}

    missions = {}
    mission_rewards = {}
    for activity in activity_table.mission_data or []:
        missions[activity.id] = activity
        mission_rewards[activity.id] = ""
        for reward in activity.rewards or []:
            mission_rewards[activity.id] += parse_reward(
                reward, item_table, building_data, character_table, skin_table
            )
    activity_text_dict = {}
    for mission in activity_table.mission_group or []:
        activity_text_dict[mission.id] = ""
        basic = basic_info[mission.id or ""]
        if (
            basic.start_time != mission.start_ts
            or basic.reward_end_time != mission.end_ts
        ):
            logger.info(f"{mission.id} time not match!")
        start_time = format_time(basic.start_time)
        end_time = format_time(basic.end_time)
        end_time2 = format_time(basic.reward_end_time)
        activity_text_dict[mission.id] += (
            table_title
            + f'\n!colspan="2"|开始时间:{start_time}<br/>结束时间:{end_time}<br/>兑换结束时间:{end_time2}'
            + "\n|-\n!内容||奖励"
        )
        for mission_id in mission.mission_ids or []:
            if missions[mission_id].mission_group != mission.id:
                logger.info(f"{mission_id} group not match!")
            activity_text_dict[mission.id] += "\n|-\n|{desc}\n|{reward}".format(
                desc=rts.compile(missions[mission_id].description).replace(
                    "\n", "<br/>"
                ),
                reward=mission_rewards[mission_id],
            )
        activity_text_dict[mission.id] += "\n|}"
    activity_text = "==活动=="
    for idx, (act_info, basic) in enumerate(basic_info.items()):
        activity_text += "\n==={name}===\n".format(name=(basic.name or "").strip())
        if idx >= 20:
            continue
        if idx >= 10:
            activity_text += "<!--\n"
        if act_info in activity_text_dict:
            activity_text += activity_text_dict[act_info]
        else:
            activity_text += '{|class = "wikitable" style = "text-align:center; display:table; white-space:normal; width:800px;"'
            activity_text += (
                f'\n!colspan="2"|开始时间:{format_time(basic.start_time)}<br/>结束时间:{format_time(basic.end_time)}<br/>兑换结束时间:{format_time(basic.reward_end_time)}'
                + "\n|}"
            )

        if basic.type == "COLLECTION":
            item_list = "\n" + table_title + '\n!colspan="8"|奖励列表\n|-'
            item_list += '\n!width="12.5%"|点数\n!width="12.5%"|奖励' * 4
            item_count = 0
            for collection in collection_acts[act_info].collections or []:
                if item_count % 4 == 0:
                    item_list += "\n|-"
                item_list += "\n|{point}\n|{item}".format(
                    point="{{{{材料消耗|{name}|{count}|50}}}}".format(
                        name=(items[collection.point_id or ""].name or "").strip(),
                        count=collection.point_cnt,
                    ),
                    item=parse_item(
                        collection.item_type,
                        collection.item_id or "",
                        collection.item_cnt,
                        item_table,
                        building_data,
                        character_table,
                        skin_table,
                        skin_count_default=-1,
                    ),
                )
                item_count += 1
            item_list += "\n|}"
            activity_text += item_list
        elif basic.type == "CHECKIN_ONLY":
            item_list = '\n{|class = "wikitable mw-collapsible mw-collapsed" style = "text-align:center; display:table; white-space:normal; width:500px;"'
            item_list += "\n!累积登录!!奖励"
            for day in (checkin_acts[act_info].check_in_list or {}).values():
                reward_list = ""
                for reward in day.item_list or []:
                    reward_list += parse_reward(
                        reward, item_table, building_data, character_table, skin_table
                    )
                item_list += f"\n|-\n|累积登录第{day.order}天\n|{reward_list}"
            item_list += "\n|}"
            activity_text += item_list
        elif basic.type == "TYPE_ACT4D0":
            act4d0 = act4d0_acts[act_info]
            token_item = act4d0.token_item
            milestone_name = (
                items[token_item.id or ""].name or "" if token_item else ""
            ).strip()
            item_list = '\n{|class = "wikitable mw-collapsible mw-collapsed" style = "text-align:center; display:table; white-space:normal; width:500px;"'
            item_list += "\n!道具点数!!奖励"
            milestone_list = {}
            order_max = 0
            for milestone in act4d0.mile_stone_item_list or []:
                order_max = max(milestone.order_id, order_max)
                milestone_list[milestone.order_id] = (
                    "\n|-\n|{{{{材料消耗|{name}|{tokenNum}|50}}}}\n|{item}".format(
                        name=milestone_name,
                        tokenNum=milestone.token_num,
                        item=parse_reward(
                            milestone.item,
                            item_table,
                            building_data,
                            character_table,
                            skin_table,
                        )
                        if milestone.item
                        else "",
                    )
                )
            for milestone in act4d0.mile_stone_story_list or []:
                order_max = max(milestone.order_id, order_max)
                milestone_list[milestone.order_id] = (
                    f"\n|-\n|{{{{材料消耗|{milestone_name}|{milestone.token_num}|50}}}}\n|{milestone.desc}"
                )
            for i in range(1, order_max + 1):
                item_list += milestone_list[i]
            item_list += "\n|}"
            activity_text += item_list
        if idx >= 10:
            activity_text += "\n-->"

    return activity_text


@job
def run(
    wiki: Wiki,
    activity_table: Annotated[ActivityTable, table("activity_table")],
    item_table: ItemTable,
    building_data: Annotated[BuildingData, table("building_data")],
    character_table: CharacterTable,
    skin_table: Annotated[SkinTable, table("skin_table")],
    rts: RichText,
) -> None:
    content = update_activity(
        activity_table, item_table, building_data, character_table, skin_table, rts
    )

    wiki.edit(title="用户:Seniorious/activities", text=content, summary="update")
    # logger.info(content)
    logger.info("Updated: {}.".format("用户:Seniorious/activities"))
