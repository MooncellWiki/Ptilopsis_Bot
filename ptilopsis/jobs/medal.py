from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel

from ptilopsis.gamedata.building_data import (
    BuildingData,
    BuildingDataCustomDataFurnitureData,
)
from ptilopsis.gamedata.character_table import CharacterData
from ptilopsis.gamedata.item_table import InventoryData, ItemData
from ptilopsis.gamedata.medal_table import (
    ItemBundle,
    MedalData,
    MedalPerData,
    MedalRarity,
)
from ptilopsis.jobs.params import CharacterTable, ItemTable, MedalTable, RichText, table
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki
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


@dataclass(frozen=True)
class RewardSources:
    """解析奖励名称要查的三张表:干员、家具、道具。"""

    character_table: dict[str, CharacterData]
    furnitures: dict[str, BuildingDataCustomDataFurnitureData]
    items: dict[str, ItemData]

    @classmethod
    def from_tables(
        cls,
        character_table: dict[str, CharacterData],
        building_data: BuildingData,
        item_table: InventoryData,
    ) -> "RewardSources":
        custom_data = building_data.custom_data
        return cls(
            character_table=character_table,
            furnitures=(custom_data.furnitures if custom_data else None) or {},
            items=item_table.items or {},
        )


def parse_reward_item(item: ItemBundle, sources: RewardSources) -> RewardView | None:
    item_id = item.id or ""
    if item.type == "CHAR":
        return RewardView(name=sources.character_table[item_id].name or "")
    if item.type == "FURN":
        return RewardView(name=sources.furnitures[item_id].name or "")
    if item_id in sources.items:
        item_name = sources.items[item_id].name or ""
        return RewardView(name=item_name.rstrip(), count=item.count)
    logger.info(f"Unknown reward item {item.id}.")
    return None


def build_rewards(medal: MedalPerData, sources: RewardSources) -> list[RewardView]:
    rewards = []
    for reward_group in medal.medal_reward_group or []:
        for item in reward_group.item_list or []:
            reward = parse_reward_item(item, sources)
            if reward is not None:
                rewards.append(reward)
    return rewards


def build_medal(
    medal: MedalPerData,
    sources: RewardSources,
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
        name=medal.medal_name or "",
        rarity=rarity,
        description=description,
        get_method=medal.get_method or "",
        has_advanced=bool(medal.advanced_medal),
        rewards=build_rewards(medal, sources),
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
    for type_key, type_data in (medal_table.medal_type_data or {}).items():
        group_data = type_data.group_data or []
        for medal_group in group_data:
            for medal_id in medal_group.medal_id or []:
                views[medal_id].group = medal_group.group_name or ""

        standalone = []
        for medal_id, raw in raw_medals.items():
            if raw.medal_type != type_key:
                continue
            view = views[medal_id]
            if view.group == "" and not raw.origin_medal:
                standalone.append(view)

        groups = []
        # 页面上套组按数据中的倒序排列(新套组在前)
        for medal_group in reversed(group_data):
            group_name = medal_group.group_name or ""
            medals = [views[medal_id] for medal_id in medal_group.medal_id or []]
            groups.append(
                GroupView(
                    name=group_name.replace("蚀刻章套组", ""),
                    title=group_name,
                    description=(medal_group.group_desc or "").replace("\n", "<br/>"),
                    medals=medals,
                    plated=any(medal.has_advanced for medal in medals),
                )
            )
        sections.append(
            SectionView(
                name=type_data.medal_name or "",
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
    medal_table: MedalData,
    character_table: dict[str, CharacterData],
    building_data: BuildingData,
    item_table: InventoryData,
    compile_rich_text: Callable[[str], str],
) -> str:
    sources = RewardSources.from_tables(character_table, building_data, item_table)
    raw_medals = {medal.medal_id or "": medal for medal in medal_table.medal_list or []}
    views = {
        medal_id: build_medal(raw, sources, compile_rich_text)
        for medal_id, raw in raw_medals.items()
    }
    resolve_medal_references(raw_medals, views)
    sections = build_sections(medal_table, raw_medals, views)
    return render_page(sections)


@job
def run(
    wiki: Wiki,
    medal_table: MedalTable,
    item_table: ItemTable,
    building_data: Annotated[BuildingData, table("building_data")],
    character_table: CharacterTable,
    rts: RichText,
) -> None:
    content = update_medal(
        medal_table, character_table, building_data, item_table, rts.compile
    )

    wiki.edit(
        title="用户:Seniorious/medal",
        text=content,
        summary="update",
        bot=None,
        minor=True,
    )
    # logger.info(content)
    logger.info("Updated: {}.".format("用户:Seniorious/medal"))
