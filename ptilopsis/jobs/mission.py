from datetime import datetime
from typing import Annotated

import pytz

from ptilopsis.gamedata.item_table import InventoryData, ItemData
from ptilopsis.gamedata.mission_table import (
    MissionDailyRewardConf,
    MissionData,
    MissionDisplayRewards,
    MissionTable,
    MissionWeeklyRewardConf,
)
from ptilopsis.jobs.params import ItemTable, RichText, table
from ptilopsis.log import logger
from ptilopsis.utils import richtext
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki

table_title = '{|class = "wikitable mw-collapsed mw-collapsible" style = "text-align:center; display:table; white-space:normal; width:800px;"'


def format_time(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, pytz.timezone("Asia/Shanghai")).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def format_rewards(
    rewards: list[MissionDisplayRewards] | None, items: dict[str, ItemData]
) -> str:
    """奖励列表渲染成连续的 {{材料消耗}};道具表里查不到的直接显示 id。"""

    content = ""
    for reward in rewards or []:
        reward_id = reward.id or ""
        content += "{{{{材料消耗|{name}|{num}}}}}".format(
            name=(items[reward_id].name or "").rstrip()
            if reward_id in items
            else reward.id,
            num=reward.count,
        )
    return content


def format_mission_row(
    mission: MissionData, mission_reward: str, rts: richtext.RichText
) -> str:
    mission_text = rts.compile(mission.description)
    return f"\n|-\n|{mission.id}\n|{mission_text}\n|{mission_reward}"


def format_reward_row(
    reward_conf: MissionDailyRewardConf | MissionWeeklyRewardConf,
    items: dict[str, ItemData],
) -> str:
    reward_content = format_rewards(reward_conf.rewards, items)
    return (
        f"\n|-\n|reward set {reward_conf.sort_index}"
        f"\n|{reward_conf.periodical_point_cost}\n|{reward_content}"
    )


def update_mission(
    mission_table: MissionTable, item_table: InventoryData, rts: richtext.RichText
) -> str:
    items = item_table.items or {}
    missions = mission_table.missions or {}
    mission_groups = mission_table.mission_groups or {}
    group_mission_list = []
    daily_text = "==日常任务=="
    count = 1
    for daily_group in mission_table.daily_mission_period_info or []:
        start_time = format_time(daily_group.start_time)
        end_time = format_time(daily_group.end_time)
        daily_text += (
            "\n"
            + f"===任务列表 {count}===\n"
            + table_title
            + f'\n!colspan="3"|开始时间:{start_time}<br/>结束时间:{end_time}'
        )
        count += 1
        daily_text += "\n|-\n!时间!!任务列表!!奖励列表"
        for period in daily_group.period_list or []:
            mission_list = '\n{|class = "wikitable mw-collapsed mw-collapsible" style = "text-align:center; display:table; white-space:normal; width:400px;"'
            mission_list += "\n!id||内容||奖励"
            mission_group = mission_groups.get(period.mission_group_id or "")
            if mission_group is None:
                continue
            for mission_id in mission_group.mission_ids or []:
                group_mission_list.append(mission_id)
                mission = missions[mission_id]
                mission_reward = ""
                if mission.periodical_point != 0:
                    mission_reward += f"Point*{mission.periodical_point}"
                mission_list += format_mission_row(mission, mission_reward, rts)
            mission_list += "\n|}"
            reward_list = '\n{|class = "wikitable mw-collapsed mw-collapsible" style = "text-align:center; display:table; white-space:normal; width:300px;"'
            reward_list += "\n!id||点数需求||奖励"
            for reward_conf in (mission_table.periodical_rewards or {}).values():
                if reward_conf.group_id == period.reward_group_id:
                    reward_list += format_reward_row(reward_conf, items)
            reward_list += "\n|}"
            daily_text += f"\n|-\n|{period.period!s}\n|{mission_list}\n|{reward_list}"
        daily_text += "\n|}"
    count = 1
    weekly_text = "==周常任务=="
    for weekly, weekly_group in mission_groups.items():
        if "weekly_g_" in weekly:
            start_time = format_time(weekly_group.start_ts)
            end_time = format_time(weekly_group.end_ts)
            weekly_text += (
                "\n"
                + f"===任务列表 {count}===\n"
                + table_title
                + f'\n!colspan="3"|开始时间:{start_time}<br/>结束时间:{end_time}'
            )
            count += 1
            weekly_text += '\n|-\n!colspan="3"|任务列表'
            weekly_text += "\n|-\n!id||内容||奖励"
            for mission_id in weekly_group.mission_ids or []:
                group_mission_list.append(mission_id)
                mission = missions[mission_id]
                mission_reward = ""
                if mission.periodical_point != 0:
                    mission_reward += f"Point*{mission.periodical_point}"
                weekly_text += format_mission_row(mission, mission_reward, rts)
            weekly_text += "\n|}"
    reward_dict = {}
    for reward_id, reward_desc in (mission_table.weekly_rewards or {}).items():
        if reward_desc.group_id not in reward_dict:
            reward_dict[reward_desc.group_id] = {}
            reward_dict[reward_desc.group_id]["start_time"] = reward_desc.begin_time
            reward_dict[reward_desc.group_id]["end_time"] = reward_desc.end_time
            start_time = format_time(reward_desc.begin_time)
            end_time = format_time(reward_desc.end_time)
            reward_dict[reward_desc.group_id]["content"] = (
                f'\n!colspan="3"|开始时间:{start_time}<br/>结束时间:{end_time}'
                + "\n|-\n!id||点数需求||奖励"
            )
        else:
            if (
                reward_dict[reward_desc.group_id]["start_time"]
                != reward_desc.begin_time
                or reward_dict[reward_desc.group_id]["end_time"] != reward_desc.end_time
            ):
                logger.info(f"{reward_id} time not match!")
        reward_dict[reward_desc.group_id]["content"] += format_reward_row(
            reward_desc, items
        )
    count = 1
    for reward_group in reward_dict:
        weekly_text += f"\n===奖励列表 {count}===\n"
        count += 1
        weekly_text += table_title + reward_dict[reward_group]["content"] + "\n|}"
    guide_text = table_title + "\n!id||内容||奖励"
    main_text = table_title + "\n!id||内容||奖励"
    sub_text = table_title + "\n!id||内容||奖励"
    remain_text = table_title + "\n!id||内容||奖励"
    for mission_key, mission in missions.items():
        if mission_key not in group_mission_list:
            mission_reward = format_rewards(mission.rewards, items)
            if mission.periodical_point != 0:
                mission_reward += f"Point*{mission.periodical_point}"
            text = format_mission_row(mission, mission_reward, rts)
            mission_id = mission.id or ""
            if "main_" in mission_id:
                main_text += text
            elif "sub_" in mission_id:
                sub_text += text
            elif "guide_" in mission_id:
                guide_text += text
            else:
                remain_text += text
    guide_text += "\n|}"
    main_text += "\n|}"
    sub_text += "\n|}"
    remain_text += "\n|}"
    mission_text = "__TOC__"
    mission_text += "\n" + daily_text
    mission_text += "\n" + weekly_text
    mission_text += "\n==见习任务==\n" + guide_text
    mission_text += "\n==主线任务==\n" + main_text
    mission_text += "\n==支线任务==\n" + sub_text
    mission_text += "\n==其他==\n" + remain_text

    return mission_text


@job
def run(
    wiki: Wiki,
    mission_table: Annotated[MissionTable, table("mission_table")],
    item_table: ItemTable,
    rts: RichText,
) -> None:
    content = update_mission(mission_table, item_table, rts)

    wiki.edit(title="用户:Seniorious/missions", text=content, summary="update")
    # logger.info(content)
    logger.info("Updated: {}.".format("用户:Seniorious/missions"))
