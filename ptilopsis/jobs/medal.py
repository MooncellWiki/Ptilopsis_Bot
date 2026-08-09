from ptilopsis.log import logger
from ptilopsis.rendering import render_wikitext
from ptilopsis.utils.job import Job
from ptilopsis.utils.richTextStyles import RichTextStyles

RARITY_ORDER = {"T1": 0, "T1D5": 1, "T2": 2, "T2D5": 3, "T3": 4, "T3D5": 5}


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


def build_medal(medal, character_table, building_data, item_table, rts):
    reward = " ".join(
        " ".join(
            parse_item(item, character_table, building_data, item_table)
            for item in item_group["itemList"]
        )
        for item_group in medal["medalRewardGroup"]
    )
    return {
        # group 与 advance_method 依赖其他奖章/套组的数据,
        # 分别由 build_sections 与 resolve_medal_references 回填
        "group": "",
        "name": medal["medalName"],
        "rarity": RARITY_ORDER.get(medal["rarity"], medal["rarity"]),
        "description": rts.compile(medal["description"].replace("\n", "<br/>"))
        if medal["description"] is not None
        else "",
        "get_method": medal["getMethod"] or "",
        "has_advanced": bool(medal["advancedMedal"]),
        "advance_method": "",
        "reward": reward,
    }


def resolve_medal_references(raw_medals, views):
    # 先补全由前置奖章数量生成的获得方式,再回填镀层方式,
    # 保证镀层方式不依赖奖章在数据中的先后顺序
    for medal_id, raw in raw_medals.items():
        view = views[medal_id]
        if view["get_method"] == "" and raw["preMedalIdList"]:
            view["get_method"] = (
                "获得{}枚前置蚀刻章（即本套组除此蚀刻章外的所有蚀刻章）".format(
                    len(raw["preMedalIdList"])
                )
            )
    for medal_id, raw in raw_medals.items():
        if raw["advancedMedal"]:
            views[medal_id]["advance_method"] = views[raw["advancedMedal"]][
                "get_method"
            ]


def build_sections(medal_table, raw_medals, views):
    sections = []
    for type_key, type_data in medal_table["medalTypeData"].items():
        for medal_group in type_data["groupData"]:
            for medal_id in medal_group["medalId"]:
                views[medal_id]["group"] = medal_group["groupName"]

        standalone = [
            views[medal_id]
            for medal_id, raw in raw_medals.items()
            if raw["medalType"] == type_key
            and views[medal_id]["group"] == ""
            and not raw["originMedal"]
        ]

        groups = []
        # 页面上套组按数据中的倒序排列(新套组在前)
        for medal_group in reversed(type_data["groupData"]):
            medals = [views[medal_id] for medal_id in medal_group["medalId"]]
            groups.append(
                {
                    "name": medal_group["groupName"].replace("蚀刻章套组", ""),
                    "title": medal_group["groupName"],
                    "description": medal_group["groupDesc"].replace("\n", "<br/>"),
                    "medals": medals,
                    "plated": any(medal["has_advanced"] for medal in medals),
                }
            )
        sections.append(
            {
                "name": type_data["medalName"],
                "standalone": standalone,
                "groups": groups,
            }
        )
    return sections


def update_medal(medal_table, character_table, building_data, item_table, rts):
    raw_medals = {medal["medalId"]: medal for medal in medal_table["medalList"]}
    views = {
        medal_id: build_medal(raw, character_table, building_data, item_table, rts)
        for medal_id, raw in raw_medals.items()
    }
    resolve_medal_references(raw_medals, views)
    sections = build_sections(medal_table, raw_medals, views)
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
