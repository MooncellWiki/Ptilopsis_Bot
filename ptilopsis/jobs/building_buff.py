from collections.abc import Callable

from pydantic import BaseModel

from ptilopsis.gamedata.building import BuildingBuff, BuildingData, RoomData
from ptilopsis.log import logger
from ptilopsis.utils.job import JobContext, job
from ptilopsis.utils.richTextStyles import RichTextStyles
from ptilopsis.wikitext import WikiTemplate

# 数据里同名技能在不同房间、不同精英阶段各有一条,buffName 区分不了,
# 页面靠括号后缀补足。键取 buffId 而不是 buffName,免得一个条目的改名
# 波及所有同名条目。
BUFF_NAME_OVERRIDES = {
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
}

# 渲染视图,字段与页面上的 wiki 模板参数一一对应


class BuffView(BaseModel):
    name: str
    room: str
    icon: str
    description: str


class RoomView(BaseModel):
    name: str
    buffs: list[BuffView]


def build_buff(
    buff: BuildingBuff,
    name: str,
    room: RoomData,
    compile_rich_text: Callable[[str], str],
) -> BuffView:
    return BuffView(
        name=name,
        room=room.name,
        icon=buff.skill_icon,
        description=compile_rich_text(buff.description),
    )


def build_rooms(
    building_data: BuildingData,
    compile_rich_text: Callable[[str], str],
) -> list[RoomView]:
    # 页面上每个房间每个技能只占一行,同名技能的重复条目不输出;
    # 保留首个条目,排序用的 sortId 也取自它
    room_buffs: dict[str, dict[str, tuple[int, BuffView]]] = {
        room_id: {} for room_id in building_data.rooms
    }
    for buff in building_data.buffs.values():
        name = BUFF_NAME_OVERRIDES.get(buff.buff_id, buff.buff_name)
        deduplicated = room_buffs[buff.room_type]
        if name in deduplicated:
            continue
        view = build_buff(
            buff,
            name,
            building_data.rooms[buff.room_type],
            compile_rich_text,
        )
        deduplicated[name] = (buff.sort_id, view)

    rooms = []
    for room_id, room in building_data.rooms.items():
        if not room_buffs[room_id]:
            continue
        # 技能按 sortId 降序排列,与游戏内技能列表的顺序一致
        sorted_buffs = sorted(
            room_buffs[room_id].values(), key=lambda item: item[0], reverse=True
        )
        rooms.append(RoomView(name=room.name, buffs=[view for _, view in sorted_buffs]))
    return rooms


def render_buff(buff: BuffView) -> str:
    template = WikiTemplate("后勤技能信息/store")
    template.add_all(
        {
            "技能名": buff.name,
            "房间": buff.room,
            "技能图标": buff.icon,
            "技能描述": buff.description,
        }
    )
    return str(template)


def render_room(room: RoomView) -> str:
    # 可折叠表格,技能之间用 |- 分隔
    buffs = "\n|-\n".join(render_buff(buff) for buff in room.buffs)
    return (
        f"=={room.name}==\n"
        '{|class="wikitable mw-collapsible mw-collapsed logo" '
        'style="text-align:center; width:100%; max-width:1000px; '
        'display:table; white-space:normal;"\n'
        f'! colspan="4" | {room.name}\n'
        "|-\n"
        '! width="30px" |\n'
        '! width="100px" |名称\n'
        '! width="520px" |描述\n'
        '! width="350px" |持有干员\n'
        "|-\n"
        f"{buffs}\n"
        "|}"
    )


def get_building_buff(
    building_data: dict,
    compile_rich_text: Callable[[str], str],
) -> str:
    table = BuildingData.model_validate(building_data)
    rooms = build_rooms(table, compile_rich_text)
    return "".join(f"{render_room(room)}\n" for room in rooms)


@job
def run(ctx: JobContext) -> None:
    building_data = ctx.getgd("excel/building_data.json")
    rts = RichTextStyles(ctx.getgd("excel/gamedata_const.json"))

    origin_text = ctx.wiki.read("后勤技能一览/store")
    flag = origin_text.find("==控制中枢==")
    head = origin_text[:flag].rstrip()
    content = head + "\n" + get_building_buff(building_data, rts.compile).rstrip()

    if content != origin_text:
        ctx.wiki.edit(
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
