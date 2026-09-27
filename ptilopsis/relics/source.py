import re
from typing import Any

from pydantic import field_validator

from ptilopsis.gamedata._base import GameDataModel
from ptilopsis.gamedata.gamedata_const import TermDescriptionData
from ptilopsis.gamedata.roguelike_topic_table import (
    RoguelikeDifficultyUpgradeRelicGroupData,
    RoguelikeGameItemData,
    RoguelikeTopicBasicData,
)
from ptilopsis.relics.render import PREAMBLE, render_relic, title_key


def keyed(value: Any) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if not isinstance(value, list):
        raise ValueError("预期字典或 key/value 数组")
    result = {}
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != {"key", "value"}:
            raise ValueError("无效 key/value 条目")
        key = entry["key"]
        if not isinstance(key, str) or key in result:
            raise ValueError(f"重复或无效 key：{key!r}")
        result[key] = entry["value"]
    return result


class RelicDetail(GameDataModel):
    items: dict[str, RoguelikeGameItemData]
    difficulty_upgrade_relic_groups: dict[str, RoguelikeDifficultyUpgradeRelicGroupData]

    @field_validator("items", "difficulty_upgrade_relic_groups", mode="before")
    @classmethod
    def decode_maps(cls, value):
        return keyed(value)


class RelicTopics(GameDataModel):
    topics: dict[str, RoguelikeTopicBasicData]
    details: dict[str, RelicDetail]

    @field_validator("topics", "details", mode="before")
    @classmethod
    def decode_maps(cls, value):
        return keyed(value)


class RelicGlossary(GameDataModel):
    term_description_dict: dict[str, TermDescriptionData]

    @field_validator("term_description_dict", mode="before")
    @classmethod
    def decode_maps(cls, value):
        return keyed(value)


def build_records(topics: RelicTopics, glossary: RelicGlossary) -> dict:
    terms = {
        term.term_name: term.description
        for term in glossary.term_description_dict.values()
        if term.term_name and term.description
    }
    records: dict[str, dict] = {}
    for theme_id, theme in sorted(topics.topics.items(), key=lambda pair: pair[1].sort):
        if not re.fullmatch(r"rogue_[1-9]\d*", theme_id) or not theme.name:
            raise ValueError(f"无法识别主题：{theme_id}")
        if theme_id not in topics.details:
            raise ValueError(f"主题缺少详情：{theme_id}")
        detail = topics.details[theme_id]
        items = {
            key: item for key, item in detail.items.items() if item.type == "RELIC"
        }
        if not items:
            raise ValueError(f"主题收藏品数据为空：{theme_id}")
        groups = {}
        for group_id, group in detail.difficulty_upgrade_relic_groups.items():
            members = sorted(
                group.relic_data or [], key=lambda member: member.equivalent_grade
            )
            if (
                not members
                or any(member.relic_id not in items for member in members)
                or [member.equivalent_grade for member in members] != [0, 3, 6, 9]
            ):
                raise ValueError(f"难度变体缺失或阈值不符合 0/3/6/9：{group_id}")
            base_name = items[members[0].relic_id].name
            for member in members:
                item_id = member.relic_id
                name = items[item_id].name or ""
                if re.sub(r"[-－]?[αβγ]$", "", name) != base_name or item_id in groups:
                    raise ValueError(f"难度变体名称或归属不明确：{item_id}")
                groups[item_id] = (group_id, base_name, member.equivalent_grade)
        slots = {}
        for item_id, item in items.items():
            if item.id != item_id or not item_id.startswith(theme_id + "_"):
                raise ValueError(f"收藏品 ID 与主题不一致：{item_id}")
            group_id, name, difficulty = groups.get(item_id, (None, item.name, 0))
            if not name:
                raise ValueError(f"收藏品缺少名称：{item_id}")
            leaf = item.model_dump(by_alias=True)
            leaf["key"] = item_id
            leaf["difficulty"] = difficulty
            description = item.description or ""
            explanations = [
                f"【{term}】{terms[term]}"
                for term in dict.fromkeys(re.findall(r"【([^】]+)】", item.usage or ""))
                if term in terms
            ]
            if explanations:
                description = (description + "\n" if description else "") + "\n".join(
                    explanations
                )
            leaf["description"] = description
            if name not in slots:
                slot = {"theme": theme.name, "value": [leaf]}
                records.setdefault(name, {"name": name, "value": []})["value"].append(
                    slot
                )
                slots[name] = (slot, group_id)
            else:
                slot, previous_group = slots[name]
                if not group_id or previous_group != group_id:
                    raise ValueError(f"主题内出现无关同名收藏品：{theme_id}/{name}")
                slot["value"].append(leaf)
        for slot, _ in slots.values():
            slot["value"].sort(key=lambda leaf: leaf["difficulty"])
    return {"relic": list(records.values())}


def render_pages(source: dict, themes: list[int] | None = None) -> list[dict]:
    records = source.get("relic") if isinstance(source, dict) else None
    if not isinstance(records, list) or not records:
        raise ValueError("收藏品来源缺少非空 relic 数组")
    pages = []
    seen = set()
    selected = set(themes or [])
    if any(type(number) is not int or number < 1 for number in selected):
        raise ValueError("主题编号必须为正整数")
    available = set()
    for record in records:
        page = render_relic(record, PREAMBLE)
        key = title_key(page["title"])
        if ":" in page["title"] or key in seen:
            raise ValueError(f"页面标题重复或包含命名空间：{page['title']}")
        seen.add(key)
        numbers = {theme["source_number"] for theme in page["themes"]}
        available.update(numbers)
        if selected:
            if not selected.intersection(numbers):
                continue
            page = render_relic(record, PREAMBLE, theme_numbers=selected)
        pages.append(page)
    missing = selected - available
    if missing:
        raise ValueError(
            "来源不存在指定主题编号："
            + ", ".join(map(str, sorted(missing)))
            + "；可用编号："
            + ", ".join(map(str, sorted(available)))
        )
    return pages
