from ptilopsis.log import logger
from ptilopsis.rendering import render_wikitext
from ptilopsis.utils.job import Job
from ptilopsis.utils.richTextStyles import RichTextStyles


def parse_item(item, character_table, building_data, item_table):
    if item["type"] == "CHAR":
        return character_table[item["id"]]["name"]
    elif item["type"] == "FURN":
        return building_data["customData"]["furnitures"][item["id"]]["name"]
    elif item["id"] in item_table["items"]:
        return "{{{{材料消耗|{}|{}}}}}".format(
            item_table["items"][item["id"]]["name"].rstrip(), item["count"]
        )
    else:
        logger.info("Unknown reward item {}.".format(item["id"]))


def update_medal(medal_table, character_table, building_data, item_table, rts):
    medal_dict = {}
    for medal_type in medal_table["medalTypeData"]:
        medal_dict[medal_type] = {}
    for medal in medal_table["medalList"]:
        reward_list = " ".join(
            [
                " ".join(
                    [
                        parse_item(item, character_table, building_data, item_table)
                        for item in item_group["itemList"]
                    ]
                )
                for item_group in medal["medalRewardGroup"]
            ]
        )
        medal_rarity = {"T1": 0, "T1D5": 1, "T2": 2, "T2D5": 3, "T3": 4, "T3D5": 5}.get(
            medal["rarity"], medal["rarity"]
        )
        medal_dict[medal["medalType"]][medal["medalId"]] = {
            "group": "",
            "name": medal["medalName"],
            "rarity": medal_rarity,
            "description": rts.compile(medal["description"].replace("\n", "<br/>"))
            if medal["description"] is not None
            else "",
            "get_method": medal["getMethod"] if medal["getMethod"] is not None else "",
            "advanced_medal": medal["advancedMedal"]
            if medal["advancedMedal"] is not None
            else "",
            "advance_method": "",
            "origin_medal": medal["originMedal"]
            if medal["originMedal"] is not None
            else "",
            "reward": reward_list,
            "prerequisite_medals": medal["preMedalIdList"],
        }
    for medal_type in medal_dict:
        for medal_key in medal_dict[medal_type]:
            medal = medal_dict[medal_type][medal_key]
            if medal["advanced_medal"] != "":
                medal["advance_method"] = medal_dict[medal_type][
                    medal["advanced_medal"]
                ]["get_method"]
            if medal["get_method"] == "" and medal["prerequisite_medals"] != []:
                medal["get_method"] = (
                    "获得{}枚前置蚀刻章（即本套组除此蚀刻章外的所有蚀刻章）".format(
                        len(medal["prerequisite_medals"])
                    )
                )
    for medal_type in medal_table["medalTypeData"]:
        for medal_group in medal_table["medalTypeData"][medal_type]["groupData"]:
            for medal_key in medal_group["medalId"]:
                medal_dict[medal_type][medal_key]["group"] = medal_group["groupName"]

    sections = []
    for medal_type in medal_table["medalTypeData"]:
        standalone = []
        for medal_key in medal_dict[medal_type]:
            medal = medal_dict[medal_type][medal_key]
            if medal["group"] == "" and medal["origin_medal"] == "":
                standalone.append(medal)

        groups = []
        for medal_group in reversed(
            medal_table["medalTypeData"][medal_type]["groupData"]
        ):
            medals = [
                medal_dict[medal_type][medal_key]
                for medal_key in medal_group["medalId"]
            ]
            groups.append(
                {
                    "name": medal_group["groupName"].replace("蚀刻章套组", ""),
                    "title": medal_group["groupName"],
                    "description": medal_group["groupDesc"].replace("\n", "<br/>"),
                    "medals": medals,
                    "plated": any(medal["advance_method"] != "" for medal in medals),
                }
            )
        sections.append(
            {
                "name": medal_table["medalTypeData"][medal_type]["medalName"],
                "standalone": standalone,
                "groups": groups,
            }
        )

    return render_wikitext("medal/page.wiki.jinja2", sections=sections)


class Medal(Job):
    def _run(self):
        medal_table = self.getgd("excel/medal_table.json")
        item_table = self.getgd("excel/item_table.json")
        building_data = self.getgd("excel/building_data.json")
        character_table = self.getgd("excel/character_table.json")
        rts = RichTextStyles(self.getgd("excel/gamedata_const.json"))

        content = update_medal(
            medal_table, character_table, building_data, item_table, rts
        )

        self.wiki.edit(
            title="用户:Seniorious/medal",
            text=content,
            summary="update",
            bot=None,
            minor=True,
        )
        # logger.info(content)
        logger.info("Updated: {}.".format("用户:Seniorious/medal"))
