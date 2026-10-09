from collections.abc import Callable
from typing import Annotated

from ptilopsis.gamedata.building_data import BuildingData
from ptilopsis.jobs.basic import BUILDING_BUFF_NAME_OVERRIDES
from ptilopsis.jobs.params import RichText, table
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki
from ptilopsis.wikitext import WikiTemplate


def render_room(name: str | None, rows: str) -> str:
    """一个房间的可折叠技能表。

    房间标题与表头骨架包在 <includeonly> 里:仅被 后勤技能一览 嵌入时渲染,
    本页保存时 Cargo 只解析骨架外的技能数据行;技能行之间不输出 |-。
    片段以 includeonly 内的状态开头和结尾:首个房间的开标签由页首头部
    (参阅模板行)提供,最后一个房间之后由调用方补上闭标签。
    """

    return (
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
        f"{rows}<includeonly>\n"
        "|}"
    )


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

    tables: list[str] = []
    for room_id, buffs in room_buffs.items():
        if not buffs:
            continue
        # 技能按 sortId 降序排列
        ordered = sorted(buffs.values(), key=lambda buff: buff[0], reverse=True)
        rows = "\n".join(text for _, text in ordered)
        tables.append(render_room(rooms[room_id].name, rows))
    return "\n".join(tables) + "</includeonly>"


@job
async def run(
    wiki: Wiki,
    building_data: Annotated[BuildingData, table("building_data")],
    rts: RichText,
) -> None:
    origin_text = await wiki.read("后勤技能一览/store")
    flag = origin_text.find("==控制中枢==")
    if flag < 0:
        # 找不到首个房间就切不出头部,硬拼会把整页旧内容当头部、技能行全部重复
        logger.error("后勤技能一览/store 里找不到 ==控制中枢==,跳过更新")
        return
    head = origin_text[:flag].rstrip()
    if head.rfind("<includeonly>") <= head.rfind("</includeonly>"):
        logger.warning(
            "后勤技能一览/store 头部末尾没有未闭合的 <includeonly>,"
            "首个房间的骨架将不被包裹"
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
