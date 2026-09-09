import time

from ptilopsis.jobs.params import CharacterTable, UniEquipTable
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki


@job
def run(
    wiki: Wiki, module_table: UniEquipTable, character_table: CharacterTable
) -> None:
    cur_ts = int(time.time())
    latest_modules_tracks = []
    for track in module_table.equip_track_dict or []:
        if track.time_stamp >= cur_ts - 2592000:  # 30*24*3600 一个月
            latest_modules_tracks.append(track)

    equip_dict = module_table.equip_dict or {}
    module_list = []
    for track in latest_modules_tracks:
        for mod in track.track_list or []:
            if mod.type != "INITIAL" and (
                mod.archive_show_time_end > cur_ts or mod.archive_show_time_end < 0
            ):
                mod_data = equip_dict[mod.equip_id or ""]
                mod_type = mod_data.type_name_2
                char_name = character_table[mod.char_id or ""].name
                module_list.append(
                    f"1={char_name}:2={mod_data.type_name_1}-{mod_type}:3={mod_data.uni_equip_name}"
                )

    content = ",".join(module_list)

    wiki.edit(
        title="首页/亮点干员/新增模组/数据",
        text=content,
        summary="update",
        bot=None,
        minor=False,
    )
    # logger.info(content)
    logger.info("Updated: {}.".format("首页/新增模组"))
