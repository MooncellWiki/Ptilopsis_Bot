from typing import Annotated, Any

from ptilopsis.gamedata.building_data import BuildingData
from ptilopsis.jobs.params import RichText, table
from ptilopsis.log import logger
from ptilopsis.utils import richtext
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki

# def special_buff(buff_name, description):
#     if buff_name == '坚毅随和':
#         description = description.replace('额外恢复心情}}', '额外恢复心情}}{{color|#F49800|（心情每小时恢复+0.15）}}')
#     elif buff_name == '神经质':
#         description += '{{color|#F49800|（心情每小时消耗+1.5）}}'
#     elif buff_name == '至察':
#         description += '{{color|#F49800|（心情每小时消耗+0.5）}}'
#     elif buff_name in ['裁缝·α', '裁缝·β']:
#         description = description.replace('影响概率）', '影响概率）{{color|#F49800|（同类效果取最高）}}')
#     return description


def get_building_buff(building_data: BuildingData, rts: richtext.RichText) -> str:
    buff_format = """{{{{后勤技能信息/store
|技能名={name}
|房间={room}
|技能图标={icon}
|技能描述={description}
}}}}"""
    room_format = """=={roomName}==
{{|class="wikitable mw-collapsible mw-collapsed logo" style="text-align:center; width:100%; max-width:1000px; display:table; white-space:normal;"
! colspan="4" | {roomName}
|-
! width="30px" |
! width="100px" |名称
! width="520px" |描述
! width="350px" |持有干员
|-
{buffInfoAll}
|}}"""
    rooms = building_data.rooms or {}
    buff_text: dict[str, dict[str, dict[str, Any]]] = {}
    for room in rooms:
        buff_text[room] = {}

    for buff_data in (building_data.buffs or {}).values():
        buff_name = buff_data.buff_name or ""
        buff_name = {
            "control_dorm_rec[000]": "领袖(控制中枢)",
            "dorm_rec_all[013]": "领袖(宿舍)",
            "train_spd_doubleProf[100]": "红龙之血(精英0)",
            "train_spd_doubleProf[110]": "红龙之血(精英2)",
            "control_token_prod_spd2[000]": "以身作则(控制中枢)",
            "train_spd&profession2[440]": "以身作则(训练室)",
            "manu_prod_spd&limit&cost[200]": "得心应手(制造站)",
            "meet_spd_condChar[000]": "得心应手(会客室)",
            "control_prod_bd_spd[000]": "丰富工作经验(精英0)",
            "control_prod_bd_spd[010]": "丰富工作经验(精英2)",
            "power_rec_spd[008]": "澎湃紊流(精英0)",
            "power_rec_spd[009]": "澎湃紊流(精英1)",
            "meet_spd[1020]": "线索搜集·β(行箸)",
        }.get(buff_data.buff_id or "", buff_name)
        if buff_name not in buff_text[buff_data.room_type]:
            buff_text[buff_data.room_type][buff_name] = {
                "sortId": buff_data.sort_id,
                "text": buff_format.format(
                    name=buff_name,
                    room=rooms[buff_data.room_type].name,
                    icon=buff_data.skill_icon,
                    # description = special_buff(buff_name, rts.compile(buff_data['description']))
                    description=rts.compile(buff_data.description),
                ),
            }

    content = ""
    for room_id in buff_text:
        if buff_text[room_id] != {}:
            content += (
                room_format.format(
                    roomName=rooms[room_id].name,
                    buffInfoAll="\n|-\n".join(
                        [
                            buff_data["text"]
                            for buff_data in sorted(
                                buff_text[room_id].values(),
                                key=lambda x: x["sortId"],
                                reverse=True,
                            )
                        ]
                    ),
                )
                + "\n"
            )
    return content


@job
async def run(
    wiki: Wiki,
    building_data: Annotated[BuildingData, table("building_data")],
    rts: RichText,
) -> None:
    origin_text = await wiki.read("后勤技能一览/store")
    flag = origin_text.find("==控制中枢==")
    head = origin_text[:flag].rstrip()
    content = head + "\n" + get_building_buff(building_data, rts).rstrip()

    if content != origin_text:
        await wiki.edit(
            title="后勤技能一览/store",
            text=content,
            summary="update",
            bot=None,
            minor=True,
        )
        # logger.info(content)
        logger.info("Updated: {}.".format("后勤技能一览/store"))
    else:
        logger.info("Same: {}.".format("后勤技能一览/store"))
