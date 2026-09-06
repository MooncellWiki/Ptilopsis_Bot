import time

from pydantic import BaseModel

from ptilopsis.gamedata.uniequip import (
    UniEquipData,
    UniEquipTable,
    UniEquipTimeInfo,
    UniEquipTrack,
    UniEquipType,
)
from ptilopsis.log import logger
from ptilopsis.utils.job import JobContext, job

RECENT_TRACK_SECONDS = 30 * 24 * 60 * 60

# 渲染视图,字段与数据页上每条模组记录的展示字段一一对应


class ModuleView(BaseModel):
    character_name: str
    type_name_1: str
    type_name_2: str
    module_name: str


def select_recent_tracks(
    table: UniEquipTable, current_timestamp: int
) -> list[UniEquipTimeInfo]:
    """保留最近 30 天内的模组发布批次,包括时间窗口的左边界。"""

    earliest_timestamp = current_timestamp - RECENT_TRACK_SECONDS
    return [
        track
        for track in table.equip_track_dict
        if track.time_stamp >= earliest_timestamp
    ]


def is_visible_module(track: UniEquipTrack, current_timestamp: int) -> bool:
    """排除初始模组及已结束展示的模组;截止时间为负表示常驻展示。"""

    return track.type != UniEquipType.INITIAL and (
        track.archive_show_time_end > current_timestamp
        or track.archive_show_time_end < 0
    )


def build_module(module: UniEquipData, character_name: str) -> ModuleView:
    return ModuleView(
        character_name=character_name,
        type_name_1=module.type_name_1,
        type_name_2=module.type_name_2,
        module_name=module.uni_equip_name,
    )


def build_modules(
    table: UniEquipTable,
    character_table: dict,
    current_timestamp: int,
) -> list[ModuleView]:
    modules = []
    for time_info in select_recent_tracks(table, current_timestamp):
        for track in time_info.track_list:
            if not is_visible_module(track, current_timestamp):
                continue
            modules.append(
                build_module(
                    table.equip_dict[track.equip_id],
                    character_table[track.char_id]["name"],
                )
            )
    return modules


def render_module(module: ModuleView) -> str:
    # 数据页存的不是 {{模板}} 调用而是 1=干员名:2=职业分支-模组代号:3=模组名
    # 的字段序列,没有参数表可言,WikiTemplate 在这里派不上用场
    return (
        f"1={module.character_name}"
        f":2={module.type_name_1}-{module.type_name_2}"
        f":3={module.module_name}"
    )


def render_modules(modules: list[ModuleView]) -> str:
    return ",".join(render_module(module) for module in modules)


def update_new_module(
    module_table: dict,
    character_table: dict,
    current_timestamp: int,
) -> str:
    table = UniEquipTable.model_validate(module_table)
    modules = build_modules(table, character_table, current_timestamp)
    return render_modules(modules)


@job
def run(ctx: JobContext) -> None:
    module_table = ctx.getgd("excel/uniequip_table.json")
    character_table = ctx.getgd("excel/character_table.json")

    content = update_new_module(
        module_table,
        character_table,
        current_timestamp=int(time.time()),
    )

    ctx.wiki.edit(
        title="首页/亮点干员/新增模组/数据",
        text=content,
        summary="update",
        bot=None,
        minor=False,
    )
    # logger.info(content)
    logger.info("Updated: {}.".format("首页/新增模组"))
