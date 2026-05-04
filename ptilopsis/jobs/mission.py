from datetime import datetime

import pytz

from ptilopsis.utils.job import Job
from ptilopsis.utils.richTextStyles import RichTextStyles

table_title = '{|class = "wikitable mw-collapsed mw-collapsible" style = "text-align:center; display:table; white-space:normal; width:800px;"'


def update_mission(mission_table, item_table, rts):
    group_mission_list = []
    daily_text = "==日常任务=="
    count = 1
    for daily_group in mission_table["dailyMissionPeriodInfo"]:
        start_time = datetime.fromtimestamp(
            daily_group["startTime"], pytz.timezone("Asia/Shanghai")
        ).strftime("%Y-%m-%d %H:%M:%S")
        end_time = datetime.fromtimestamp(
            daily_group["endTime"], pytz.timezone("Asia/Shanghai")
        ).strftime("%Y-%m-%d %H:%M:%S")
        daily_text += (
            "\n"
            + f"===任务列表 {count}===\n"
            + table_title
            + f'\n!colspan="3"|开始时间:{start_time}<br/>结束时间:{end_time}'
        )
        count += 1
        daily_text += "\n|-\n!时间!!任务列表!!奖励列表"
        for period in daily_group["periodList"]:
            mission_list = '\n{|class = "wikitable mw-collapsed mw-collapsible" style = "text-align:center; display:table; white-space:normal; width:400px;"'
            mission_list += "\n!id||内容||奖励"
            if period["missionGroupId"] not in mission_table["missionGroups"]:
                continue
            for mission_id in mission_table["missionGroups"][period["missionGroupId"]][
                "missionIds"
            ]:
                group_mission_list.append(mission_id)
                mission_reward = ""
                if mission_table["missions"][mission_id]["periodicalPoint"] != 0:
                    mission_reward += "Point*{}".format(
                        mission_table["missions"][mission_id]["periodicalPoint"]
                    )
                mission_list += (
                    "\n|-\n|{mission_id}\n|{mission_text}\n|{mission_reward}".format(
                        mission_id=mission_table["missions"][mission_id]["id"],
                        mission_text=rts.compile(
                            mission_table["missions"][mission_id]["description"]
                        ),
                        mission_reward=mission_reward,
                    )
                )
            mission_list += "\n|}"
            reward_list = '\n{|class = "wikitable mw-collapsed mw-collapsible" style = "text-align:center; display:table; white-space:normal; width:300px;"'
            reward_list += "\n!id||点数需求||奖励"
            for reward_id in mission_table["periodicalRewards"]:
                if (
                    mission_table["periodicalRewards"][reward_id]["groupId"]
                    == period["rewardGroupId"]
                ):
                    reward_content = ""
                    if mission_table["periodicalRewards"][reward_id]["rewards"]:
                        for reward in mission_table["periodicalRewards"][reward_id][
                            "rewards"
                        ]:
                            reward_content += "{{{{材料消耗|{name}|{num}}}}}".format(
                                name=item_table["items"][reward["id"]]["name"].rstrip()
                                if reward["id"] in item_table["items"]
                                else reward["id"],
                                num=reward["count"],
                            )
                    reward_list += "\n|-\n|reward set {sort_id}\n|{pointCost}\n|{reward_content}".format(
                        sort_id=mission_table["periodicalRewards"][reward_id][
                            "sortIndex"
                        ],
                        pointCost=mission_table["periodicalRewards"][reward_id][
                            "periodicalPointCost"
                        ],
                        reward_content=reward_content,
                    )
            reward_list += "\n|}"
            daily_text += "\n|-\n|{period}\n|{mission_list}\n|{reward_list}".format(
                period=str(period["period"]),
                mission_list=mission_list,
                reward_list=reward_list,
            )
        daily_text += "\n|}"
    count = 1
    weekly_text = "==周常任务=="
    for weekly in mission_table["missionGroups"]:
        if "weekly_g_" in weekly:
            start_time = datetime.fromtimestamp(
                mission_table["missionGroups"][weekly]["startTs"],
                pytz.timezone("Asia/Shanghai"),
            ).strftime("%Y-%m-%d %H:%M:%S")
            end_time = datetime.fromtimestamp(
                mission_table["missionGroups"][weekly]["endTs"],
                pytz.timezone("Asia/Shanghai"),
            ).strftime("%Y-%m-%d %H:%M:%S")
            weekly_text += (
                "\n"
                + f"===任务列表 {count}===\n"
                + table_title
                + f'\n!colspan="3"|开始时间:{start_time}<br/>结束时间:{end_time}'
            )
            count += 1
            weekly_text += '\n|-\n!colspan="3"|任务列表'
            weekly_text += "\n|-\n!id||内容||奖励"
            for mission_id in mission_table["missionGroups"][weekly]["missionIds"]:
                group_mission_list.append(mission_id)
                mission_reward = ""
                if mission_table["missions"][mission_id]["periodicalPoint"] != 0:
                    mission_reward += "Point*{}".format(
                        mission_table["missions"][mission_id]["periodicalPoint"]
                    )
                weekly_text += (
                    "\n|-\n|{mission_id}\n|{mission_text}\n|{mission_reward}".format(
                        mission_id=mission_table["missions"][mission_id]["id"],
                        mission_text=rts.compile(
                            mission_table["missions"][mission_id]["description"]
                        ),
                        mission_reward=mission_reward,
                    )
                )
            weekly_text += "\n|}"
    reward_dict = {}
    for reward_id in mission_table["weeklyRewards"]:
        reward_desc = mission_table["weeklyRewards"][reward_id]
        if reward_desc["groupId"] not in reward_dict:
            reward_dict[reward_desc["groupId"]] = {}
            reward_dict[reward_desc["groupId"]]["start_time"] = reward_desc["beginTime"]
            reward_dict[reward_desc["groupId"]]["end_time"] = reward_desc["endTime"]
            start_time = datetime.fromtimestamp(
                reward_desc["beginTime"], pytz.timezone("Asia/Shanghai")
            ).strftime("%Y-%m-%d %H:%M:%S")
            end_time = datetime.fromtimestamp(
                reward_desc["endTime"], pytz.timezone("Asia/Shanghai")
            ).strftime("%Y-%m-%d %H:%M:%S")
            reward_dict[mission_table["weeklyRewards"][reward_id]["groupId"]][
                "content"
            ] = (
                f'\n!colspan="3"|开始时间:{start_time}<br/>结束时间:{end_time}'
                + "\n|-\n!id||点数需求||奖励"
            )
        else:
            if (
                reward_dict[reward_desc["groupId"]]["start_time"]
                != reward_desc["beginTime"]
                or reward_dict[reward_desc["groupId"]]["end_time"]
                != reward_desc["endTime"]
            ):
                print(reward_id, "time not match!")
        reward_content = ""
        if reward_desc["rewards"]:
            for reward in reward_desc["rewards"]:
                reward_content += "{{{{材料消耗|{name}|{num}}}}}".format(
                    name=item_table["items"][reward["id"]]["name"].rstrip()
                    if reward["id"] in item_table["items"]
                    else reward["id"],
                    num=reward["count"],
                )
        reward_dict[reward_desc["groupId"]]["content"] += (
            "\n|-\n|reward set {sort_id}\n|{pointCost}\n|{reward_content}".format(
                sort_id=reward_desc["sortIndex"],
                pointCost=reward_desc["periodicalPointCost"],
                reward_content=reward_content,
            )
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
    for mission in mission_table["missions"]:
        if mission not in group_mission_list:
            mission_reward = ""
            if mission_table["missions"][mission]["rewards"]:
                for reward in mission_table["missions"][mission]["rewards"]:
                    mission_reward += "{{{{材料消耗|{name}|{num}}}}}".format(
                        name=item_table["items"][reward["id"]]["name"].rstrip()
                        if reward["id"] in item_table["items"]
                        else reward["id"],
                        num=reward["count"],
                    )
            if mission_table["missions"][mission]["periodicalPoint"] != 0:
                mission_reward += "Point*{}".format(
                    mission_table["missions"][mission]["periodicalPoint"]
                )
            text = "\n|-\n|{mission_id}\n|{mission_text}\n|{mission_reward}".format(
                mission_id=mission_table["missions"][mission]["id"],
                mission_text=rts.compile(
                    mission_table["missions"][mission]["description"]
                ),
                mission_reward=mission_reward,
            )
            if "main_" in mission_table["missions"][mission]["id"]:
                main_text += text
            elif "sub_" in mission_table["missions"][mission]["id"]:
                sub_text += text
            elif "guide_" in mission_table["missions"][mission]["id"]:
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


class Mission(Job):
    def _run(self):
        mission_table = self.getgd("excel/mission_table.json")
        item_table = self.getgd("excel/item_table.json")
        rts = RichTextStyles(self.getgd("excel/gamedata_const.json"))

        content = update_mission(mission_table, item_table, rts)

        self.wiki.edit(title="用户:Seniorious/missions", text=content, summary="update")
        # print(content)
        print("Updated: {}.".format("用户:Seniorious/missions"))
