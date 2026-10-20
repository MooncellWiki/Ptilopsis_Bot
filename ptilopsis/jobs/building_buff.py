from collections.abc import Callable
from typing import Annotated

from ptilopsis.gamedata.building_data import BuildingData
from ptilopsis.jobs.basic import BUILDING_BUFF_NAME_OVERRIDES
from ptilopsis.jobs.params import RichText, table
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki
from ptilopsis.wikitext import WikiTemplate


def get_building_buff(
    building_data: BuildingData, compile_rich_text: Callable[[str | None], str]
) -> dict[str, str]:
    """生成每个技能的独立页面,同名技能只输出首条。"""
    rooms = building_data.rooms or {}
    pages: dict[str, str] = {}
    for buff in (building_data.buffs or {}).values():
        name = BUILDING_BUFF_NAME_OVERRIDES.get(
            buff.buff_id or "", buff.buff_name or ""
        )
        title = f"后勤技能一览/{name}"
        if title in pages:
            continue
        template = WikiTemplate("后勤技能信息/store").add_all(
            {
                "技能名": name,
                "sortId": buff.sort_id,
                "房间": rooms[buff.room_type].name,
                "技能图标": buff.skill_icon,
                "技能描述": compile_rich_text(buff.description),
            }
        )
        pages[title] = str(template)
    return pages


@job
async def run(
    wiki: Wiki,
    building_data: Annotated[BuildingData, table("building_data")],
    rts: RichText,
) -> None:
    pages = get_building_buff(building_data, rts.compile)
    origin_texts = await wiki.read_many(pages)
    for title, content in pages.items():
        if content == origin_texts.get(title):
            logger.info("Same: {}.", title)
            continue
        await wiki.edit(
            title=title,
            text=content,
            summary="update",
            bot=None,
            minor=True,
        )
        logger.info("Updated: {}.", title)
