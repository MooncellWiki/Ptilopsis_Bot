from collections.abc import Callable
from typing import Annotated

from ptilopsis.gamedata.building_data import BuildingData
from ptilopsis.jobs.basic import BUILDING_BUFF_NAME_OVERRIDES
from ptilopsis.jobs.params import RichText, table
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki
from ptilopsis.wikitext import WikiTemplate


def render_room(
    name: str | None, rows: str, *, first: bool = False, last: bool = False
) -> str:
    """一个房间的可折叠技能表。

    房间标题与表头骨架包在 <includeonly> 里:仅被 后勤技能一览 嵌入时渲染,
    本页保存时 Cargo 只解析骨架外的技能数据行;技能行之间不输出 |-。
    首个房间的开标签由页首头部(参阅模板行)提供,末个房间在表格收尾后闭合。
    """

    parts: list[str] = []
    if not first:
        # 接在上一房间最后一行技能的 }} 之后:先收掉上一张表,再进入本房间
        parts.append("<includeonly>\n|}\n")
    parts.append(
        f"=={name}==\n"
        '{|class="wikitable mw-collapsible mw-collapsed logo" '
        'style="text-align:center; width:100%; max-width:1000px; '
        'display:table; white-space:normal;"\n'
        f'! colspan="4" | {name}\n'
        "|-\n"
        '! width="30px" |\n'
        '! width="100px" |名称\n'
        '! width="520px" |描述\n'
        '! width="350px" |持有干员</includeonly>\n'
        f"{rows}"
    )
    if last:
        parts.append("<includeonly>\n|}</includeonly>")
    return "".join(parts)


def get_building_buff(
    building_data: BuildingData, compile_rich_text: Callable[[str | None], str]
) -> str:
    rooms = building_data.rooms or {}
    # 每个房间里同名技能只输出首条,排序用的 sortId 也取自首条
    room_buffs: dict[str, dict[str, tuple[int, str]]] = {room: {} for room in rooms}
    for buff in (building_data.buffs or {}).values():
        name = BUILDING_BUFF_NAME_OVERRIDES.get(
            buff.buff_id or "", buff.buff_name or ""
        )
        buffs = room_buffs[buff.room_type]
        if name in buffs:
            continue
        template = WikiTemplate("后勤技能信息/store").add_all(
            {
                "技能名": name,
                "房间": rooms[buff.room_type].name,
                "技能图标": buff.skill_icon,
                "技能描述": compile_rich_text(buff.description),
            }
        )
        buffs[name] = (buff.sort_id, str(template))

    used_rooms = [(room_id, buffs) for room_id, buffs in room_buffs.items() if buffs]
    content = ""
    for index, (room_id, buffs) in enumerate(used_rooms):
        # 技能按 sortId 降序排列
        ordered = sorted(buffs.values(), key=lambda buff: buff[0], reverse=True)
        rows = "\n".join(text for _, text in ordered)
        content += render_room(
            rooms[room_id].name,
            rows,
            first=index == 0,
            last=index == len(used_rooms) - 1,
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
    if "<includeonly>" not in head:
        logger.warning(
            "后勤技能一览/store 头部没有 <includeonly> 开标签,首个房间的骨架将不被包裹"
        )
    content = head + "\n" + get_building_buff(building_data, rts.compile).rstrip()

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
