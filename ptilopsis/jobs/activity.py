from datetime import datetime

import pytz

from ptilopsis.log import logger
from ptilopsis.utils.job import JobContext, job
from ptilopsis.utils.richTextStyles import RichTextStyles

table_title = '{|class = "wikitable mw-collapsible mw-collapsed" style = "text-align:center; display:table; white-space:normal; width:800px;"'


def parse_reward(reward, item_table, building_data, character_table, skin_table):
    if reward["type"] == "FURN":
        return "{{{{关卡报酬|家具=yes|{name}||50}}}}".format(
            name=building_data["customData"]["furnitures"][reward["id"]]["name"]
        )
    elif reward["type"] == "CHAR":
        return "{{{{招聘合同|{name}|50}}}}".format(
            name=character_table[reward["id"]]["name"]
        )
    elif reward["type"] == "CHAR_SKIN":
        skin_count = 0
        char_key = skin_table["charSkins"][reward["id"]]["charId"] + "@"
        skin_list = [
            skin_table["charSkins"][skin_id]
            for skin_id in skin_table["charSkins"]
            if char_key in skin_id
        ]
        skin_list.sort(
            key=lambda x: x["displaySkin"]["onYear"] * 12 + x["displaySkin"]["onPeriod"]
        )
        for skin_data in skin_list:
            if skin_data["skinId"] == reward["id"]:
                skin_count = skin_list.index(skin_data) + 1
        return "{{{{皮肤头像|{name}|50|{no}}}}}".format(
            name=character_table[skin_table["charSkins"][reward["id"]]["charId"]][
                "name"
            ],
            no=skin_count,
        )
    else:
        return "{{{{材料消耗|{name}|{count}|50}}}}".format(
            name=item_table["items"][reward["id"]]["name"].strip()
            if reward["id"] in item_table["items"]
            else reward["id"],
            count=reward["count"],
        )


def parse_collection(
    collection, item_table, building_data, character_table, skin_table
):
    if collection["itemType"] == "FURN":
        return "{{{{关卡报酬|家具=yes|{name}||50}}}}".format(
            name=building_data["customData"]["furnitures"][collection["itemId"]]["name"]
        )
    elif collection["itemType"] == "CHAR":
        return "{{{{招聘合同|{name}|50}}}}".format(
            name=character_table[collection["itemId"]]["name"]
        )
    elif collection["itemType"] == "CHAR_SKIN":
        skin_count = -1
        char_key = skin_table["charSkins"][collection["itemId"]]["charId"] + "@"
        skin_list = [
            skin_table["charSkins"][skin_id]
            for skin_id in skin_table["charSkins"]
            if char_key in skin_id
        ]
        skin_list.sort(
            key=lambda x: x["displaySkin"]["onYear"] * 12 + x["displaySkin"]["onPeriod"]
        )
        for skin_data in skin_list:
            if skin_data["skinId"] == collection["itemId"]:
                skin_count = skin_list.index(skin_data) + 1
        return "{{{{皮肤头像|{name}|50|{no}}}}}".format(
            name=character_table[
                skin_table["charSkins"][collection["itemId"]]["charId"]
            ]["name"],
            no=skin_count,
        )
    else:
        return "{{{{材料消耗|{name}|{count}|50}}}}".format(
            name=item_table["items"][collection["itemId"]]["name"].strip()
            if collection["itemId"] in item_table["items"]
            else collection["itemId"],
            count=collection["itemCnt"],
        )


def update_activity(
    activity_table, item_table, building_data, character_table, skin_table, rts
):
    activity_dict = {}
    for activity in activity_table["missionData"]:
        activity_dict[activity["id"]] = {
            "id": activity["id"],
            "description": activity["description"],
            "missionGroup": activity["missionGroup"],
            "rewards": "",
        }
        if activity["rewards"]:
            for reward in activity["rewards"]:
                activity_dict[activity["id"]]["rewards"] += parse_reward(
                    reward, item_table, building_data, character_table, skin_table
                )
        else:
            activity_dict[activity["id"]]["rewards"] += ""
    activity_text_dict = {}
    for mission in activity_table["missionGroup"]:
        activity_text_dict[mission["id"]] = ""
        if (
            activity_table["basicInfo"][mission["id"]]["startTime"]
            != mission["startTs"]
            or activity_table["basicInfo"][mission["id"]]["rewardEndTime"]
            != mission["endTs"]
        ):
            logger.info(mission["id"], "time not match!")
        start_time = datetime.fromtimestamp(
            activity_table["basicInfo"][mission["id"]]["startTime"],
            pytz.timezone("Asia/Shanghai"),
        ).strftime("%Y-%m-%d %H:%M:%S")
        end_time = datetime.fromtimestamp(
            activity_table["basicInfo"][mission["id"]]["endTime"],
            pytz.timezone("Asia/Shanghai"),
        ).strftime("%Y-%m-%d %H:%M:%S")
        end_time2 = datetime.fromtimestamp(
            activity_table["basicInfo"][mission["id"]]["rewardEndTime"],
            pytz.timezone("Asia/Shanghai"),
        ).strftime("%Y-%m-%d %H:%M:%S")
        activity_text_dict[mission["id"]] += (
            table_title
            + f'\n!colspan="2"|开始时间:{start_time}<br/>结束时间:{end_time}<br/>兑换结束时间:{end_time2}'
            + "\n|-\n!内容||奖励"
        )
        for mission_id in mission["missionIds"]:
            if activity_dict[mission_id]["missionGroup"] != mission["id"]:
                logger.info(mission_id, "group not match!")
            activity_text_dict[mission["id"]] += "\n|-\n|{desc}\n|{reward}".format(
                desc=rts.compile(activity_dict[mission_id]["description"]).replace(
                    "\n", "<br/>"
                ),
                reward=activity_dict[mission_id]["rewards"],
            )
        activity_text_dict[mission["id"]] += "\n|}"
    activity_text = "==活动=="
    for idx, act_info in enumerate(activity_table["basicInfo"]):
        activity_text += "\n==={name}===\n".format(
            name=activity_table["basicInfo"][act_info]["name"].strip()
        )
        if idx >= 20:
            continue
        if idx >= 10:
            activity_text += "<!--\n"
        if act_info in activity_text_dict:
            activity_text += activity_text_dict[act_info]
        else:
            activity_text += '{|class = "wikitable" style = "text-align:center; display:table; white-space:normal; width:800px;"'
            activity_text += (
                '\n!colspan="2"|开始时间:{s_t}<br/>结束时间:{e_t}<br/>兑换结束时间:{e_t2}'.format(
                    s_t=datetime.fromtimestamp(
                        activity_table["basicInfo"][act_info]["startTime"],
                        pytz.timezone("Asia/Shanghai"),
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    e_t=datetime.fromtimestamp(
                        activity_table["basicInfo"][act_info]["endTime"],
                        pytz.timezone("Asia/Shanghai"),
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    e_t2=datetime.fromtimestamp(
                        activity_table["basicInfo"][act_info]["rewardEndTime"],
                        pytz.timezone("Asia/Shanghai"),
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                )
                + "\n|}"
            )

        if activity_table["basicInfo"][act_info]["type"] == "COLLECTION":
            item_list = "\n" + table_title + '\n!colspan="8"|奖励列表\n|-'
            item_list += '\n!width="12.5%"|点数\n!width="12.5%"|奖励' * 4
            item_count = 0
            for collection in activity_table["activity"]["COLLECTION"][act_info][
                "collections"
            ]:
                if item_count % 4 == 0:
                    item_list += "\n|-"
                item_list += "\n|{point}\n|{item}".format(
                    point="{{{{材料消耗|{name}|{count}|50}}}}".format(
                        name=item_table["items"][collection["pointId"]]["name"].strip(),
                        count=collection["pointCnt"],
                    ),
                    item=parse_collection(
                        collection,
                        item_table,
                        building_data,
                        character_table,
                        skin_table,
                    ),
                )
                item_count += 1
            item_list += "\n|}"
            activity_text += item_list
        elif activity_table["basicInfo"][act_info]["type"] == "CHECKIN_ONLY":
            item_list = '\n{|class = "wikitable mw-collapsible mw-collapsed" style = "text-align:center; display:table; white-space:normal; width:500px;"'
            item_list += "\n!累积登录!!奖励"
            for day in activity_table["activity"]["CHECKIN_ONLY"][act_info][
                "checkInList"
            ]:
                reward_list = ""
                for reward in activity_table["activity"]["CHECKIN_ONLY"][act_info][
                    "checkInList"
                ][day]["itemList"]:
                    reward_list += parse_reward(
                        reward, item_table, building_data, character_table, skin_table
                    )
                item_list += "\n|-\n|累积登录第{days}天\n|{item}".format(
                    days=activity_table["activity"]["CHECKIN_ONLY"][act_info][
                        "checkInList"
                    ][day]["order"],
                    item=reward_list,
                )
            item_list += "\n|}"
            activity_text += item_list
        elif activity_table["basicInfo"][act_info]["type"] == "TYPE_ACT4D0":
            milestone_name = item_table["items"][
                activity_table["activity"]["TYPE_ACT4D0"][act_info]["tokenItem"]["id"]
            ]["name"].strip()
            item_list = '\n{|class = "wikitable mw-collapsible mw-collapsed" style = "text-align:center; display:table; white-space:normal; width:500px;"'
            item_list += "\n!道具点数!!奖励"
            milestone_list = {}
            order_max = 0
            for milestone in activity_table["activity"]["TYPE_ACT4D0"][act_info][
                "mileStoneItemList"
            ]:
                order_max = max(milestone["orderId"], order_max)
                milestone_list[milestone["orderId"]] = (
                    "\n|-\n|{{{{材料消耗|{name}|{tokenNum}|50}}}}\n|{item}".format(
                        name=milestone_name,
                        tokenNum=milestone["tokenNum"],
                        item=parse_reward(
                            milestone["item"],
                            item_table,
                            building_data,
                            character_table,
                            skin_table,
                        ),
                    )
                )
            for milestone in activity_table["activity"]["TYPE_ACT4D0"][act_info][
                "mileStoneStoryList"
            ]:
                order_max = max(milestone["orderId"], order_max)
                milestone_list[milestone["orderId"]] = (
                    "\n|-\n|{{{{材料消耗|{name}|{tokenNum}|50}}}}\n|{desc}".format(
                        name=milestone_name,
                        tokenNum=milestone["tokenNum"],
                        desc=milestone["desc"],
                    )
                )
            for i in range(1, order_max + 1):
                item_list += milestone_list[i]
            item_list += "\n|}"
            activity_text += item_list
        if idx >= 10:
            activity_text += "\n-->"

    return activity_text


@job
def run(ctx: JobContext) -> None:
    activity_table = ctx.getgd("excel/activity_table.json")
    item_table = ctx.getgd("excel/item_table.json")
    building_data = ctx.getgd("excel/building_data.json")
    character_table = ctx.getgd("excel/character_table.json")
    skin_table = ctx.getgd("excel/skin_table.json")
    rts = RichTextStyles(ctx.getgd("excel/gamedata_const.json"))

    content = update_activity(
        activity_table, item_table, building_data, character_table, skin_table, rts
    )

    ctx.wiki.edit(title="用户:Seniorious/activities", text=content, summary="update")
    # logger.info(content)
    logger.info("Updated: {}.".format("用户:Seniorious/activities"))
