from collections.abc import Callable

from pydantic import BaseModel

from ptilopsis.gamedata.medal import (
    ItemBundle,
    MedalData,
    MedalPerData,
    MedalRarity,
)
from ptilopsis.log import logger
from ptilopsis.utils.job import Job
from ptilopsis.utils.richTextStyles import RichTextStyles
from ptilopsis.wikitext import WikiTemplate, inline_template

# 渲染视图,字段与页面上的 wiki 模板参数一一对应


class RewardView(BaseModel):
    name: str
    # 有数量的物品渲染为 {{材料消耗}},无数量(干员/家具)直接显示名称
    count: int | None = None


class MedalView(BaseModel):
    name: str
    rarity: int | str
    description: str
    get_method: str
    has_advanced: bool
    rewards: list[RewardView]
    # group 与 advance_method 依赖其他奖章/套组的数据,
    # 分别由 build_sections 与 resolve_medal_references 回填
    group: str = ""
    advance_method: str = ""


class GroupView(BaseModel):
    name: str
    title: str
    description: str
    medals: list[MedalView]
    plated: bool


class SectionView(BaseModel):
    name: str
    standalone: list[MedalView]
    groups: list[GroupView]


def parse_reward_item(
    item: ItemBundle, character_table: dict, building_data: dict, item_table: dict
) -> RewardView | None:
    if item.type == "CHAR":
        return RewardView(name=character_table[item.id]["name"])
    if item.type == "FURN":
        furnitures = building_data["customData"]["furnitures"]
        return RewardView(name=furnitures[item.id]["name"])
    if item.id in item_table["items"]:
        item_name = item_table["items"][item.id]["name"]
        return RewardView(name=item_name.rstrip(), count=item.count)
    logger.info(f"Unknown reward item {item.id}.")
    return None


def build_rewards(
    medal: MedalPerData,
    character_table: dict,
    building_data: dict,
    item_table: dict,
) -> list[RewardView]:
    rewards = []
    for reward_group in medal.medal_reward_group:
        for item in reward_group.item_list:
            reward = parse_reward_item(item, character_table, building_data, item_table)
            if reward is not None:
                rewards.append(reward)
    return rewards


def build_medal(
    medal: MedalPerData,
    character_table: dict,
    building_data: dict,
    item_table: dict,
    compile_rich_text: Callable[[str], str],
) -> MedalView:
    description = ""
    if medal.description is not None:
        description = compile_rich_text(medal.description.replace("\n", "<br/>"))

    if medal.rarity in MedalRarity.__members__:
        rarity = MedalRarity[medal.rarity].value
    else:
        rarity = medal.rarity

    return MedalView(
        name=medal.medal_name,
        rarity=rarity,
        description=description,
        get_method=medal.get_method or "",
        has_advanced=bool(medal.advanced_medal),
        rewards=build_rewards(medal, character_table, building_data, item_table),
    )


def resolve_medal_references(
    raw_medals: dict[str, MedalPerData], views: dict[str, MedalView]
) -> None:
    # 先补全由前置奖章数量生成的获得方式,再回填镀层方式,
    # 保证镀层方式不依赖奖章在数据中的先后顺序
    for medal_id, raw in raw_medals.items():
        view = views[medal_id]
        if view.get_method == "" and raw.pre_medal_id_list:
            view.get_method = (
                f"获得{len(raw.pre_medal_id_list)}枚前置蚀刻章"
                "（即本套组除此蚀刻章外的所有蚀刻章）"
            )
    for medal_id, raw in raw_medals.items():
        if raw.advanced_medal:
            views[medal_id].advance_method = views[raw.advanced_medal].get_method


def build_sections(
    medal_table: MedalData,
    raw_medals: dict[str, MedalPerData],
    views: dict[str, MedalView],
) -> list[SectionView]:
    sections = []
    for type_key, type_data in medal_table.medal_type_data.items():
        for medal_group in type_data.group_data:
            for medal_id in medal_group.medal_id:
                views[medal_id].group = medal_group.group_name

        standalone = []
        for medal_id, raw in raw_medals.items():
            if raw.medal_type != type_key:
                continue
            view = views[medal_id]
            if view.group == "" and not raw.origin_medal:
                standalone.append(view)

        groups = []
        # 页面上套组按数据中的倒序排列(新套组在前)
        for medal_group in reversed(type_data.group_data):
            medals = [views[medal_id] for medal_id in medal_group.medal_id]
            groups.append(
                GroupView(
                    name=medal_group.group_name.replace("蚀刻章套组", ""),
                    title=medal_group.group_name,
                    description=medal_group.group_desc.replace("\n", "<br/>"),
                    medals=medals,
                    plated=any(medal.has_advanced for medal in medals),
                )
            )
        sections.append(
            SectionView(
                name=type_data.medal_name,
                standalone=standalone,
                groups=groups,
            )
        )
    return sections


def render_reward(reward: RewardView) -> str:
    # 有数量的物品渲染为 {{材料消耗}},无数量的(干员/家具)直接显示名称
    if reward.count is None:
        return reward.name
    return inline_template("材料消耗", reward.name, reward.count)


def render_rewards(rewards: list[RewardView]) -> str:
    return " ".join(render_reward(reward) for reward in rewards)


def render_medal(medal: MedalView) -> str:
    template = WikiTemplate("蚀刻章")
    template.add_optional("套组", medal.group)
    template.add("名称", medal.name)
    template.add("稀有度", medal.rarity)
    template.add("描述", medal.description)
    template.add("获得方式", medal.get_method)
    # 有镀层的奖章即使镀层方式为空也要留下这个参数
    if medal.has_advanced:
        template.add("镀层方式", medal.advance_method)
    template.add_optional("奖励", render_rewards(medal.rewards))
    return str(template)


def render_group(group: GroupView) -> str:
    template = WikiTemplate("蚀刻章/套组预览")
    template.add("名称", group.name)
    if group.plated:
        template.add("镀层", 1)
    template.add("标题名称", group.title)
    template.add("标题背景", "")
    template.add("介绍", group.description)
    medals = "\n".join(render_medal(medal) for medal in group.medals)
    template.add_block("内容", medals)
    return f"==={group.title}===\n{template}"


def render_section(section: SectionView) -> str:
    # 二级标题 + 独立奖章 + 套组预览(新套组在前,顺序由 build_sections 决定)
    blocks = [f"=={section.name}=="]
    blocks.extend(render_medal(medal) for medal in section.standalone)
    blocks.extend(render_group(group) for group in section.groups)
    return "\n".join(blocks)


def render_page(sections: list[SectionView]) -> str:
    return "".join(f"{render_section(section)}\n" for section in sections)


def update_medal(
    medal_table: dict,
    character_table: dict,
    building_data: dict,
    item_table: dict,
    compile_rich_text: Callable[[str], str],
) -> str:
    table = MedalData.model_validate(medal_table)
    raw_medals = {medal.medal_id: medal for medal in table.medal_list}
    views = {
        medal_id: build_medal(
            raw, character_table, building_data, item_table, compile_rich_text
        )
        for medal_id, raw in raw_medals.items()
    }
    resolve_medal_references(raw_medals, views)
    sections = build_sections(table, raw_medals, views)
    return render_page(sections)


class Medal(Job):
    def _run(self):
        medal_table = self.getgd("excel/medal_table.json")
        item_table = self.getgd("excel/item_table.json")
        building_data = self.getgd("excel/building_data.json")
        character_table = self.getgd("excel/character_table.json")
        rts = RichTextStyles(self.getgd("excel/gamedata_const.json"))

        content = update_medal(
            medal_table, character_table, building_data, item_table, rts.compile
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
