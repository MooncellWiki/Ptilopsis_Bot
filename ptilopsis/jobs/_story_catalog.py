"""把国服剧情回顾表和 Wiki 特例合成剧情页目录。"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import anyio

from ptilopsis.config import get_settings
from ptilopsis.gamedata._base import GameDataModel
from ptilopsis.jobs.params import CharacterTable, StoryReviewTable
from ptilopsis.log import logger
from ptilopsis.utils.di import Depends
from ptilopsis.utils.wiki import Wiki

MEMORY_GROUP = re.compile(r"story_(.+)_set_(\d+)")
SCRIPT_PATH = re.compile(r"[\w\[\].-]+(?:/[\w\[\].-]+)+")
RULES_PATH = Path(__file__).with_name("story_rules.json")


class Variation(GameDataModel):
    id: str


class StoryEntry(GameDataModel):
    story_id: str | None = None
    story_group: str | None = None
    story_sort: float = 0
    story_can_show: int = 0
    story_review_type: str = "NONE"
    story_code: str | None = None
    story_name: str | None = None
    avg_tag: str | None = None
    story_txt: str | None = None
    story_variation: Variation | None = None
    wiki_type: str | None = None
    wiki_group: str | None = None


class ManualRow(GameDataModel):
    name: str
    story_type: str | None = None
    info_unlock_datas: list[StoryEntry]


class ManualGroup(GameDataModel):
    story_type: str | None = None
    group_datas: list[ManualRow]


class StoryRules(GameDataModel):
    act_code: dict[str, str]
    act_type: dict[str, str]
    avg_tag: dict[str, str]
    append: dict[str, StoryEntry]
    override: dict[str, dict[str, StoryEntry]]
    navigation: dict[str, list[ManualGroup]]


@dataclass(frozen=True)
class Script:
    path: str
    title: str
    kind: str
    group: str


@dataclass(frozen=True)
class StoryCatalog:
    stories: dict[str, Script]
    ambiguous_paths: set[str]
    complete: set[str]


def title_key(title: str) -> str:
    """Wiki 将下划线和连续空白规范化成单个空格。"""
    return " ".join(title.replace("_", " ").split())


def script_path(path: str) -> str:
    return path.strip().removesuffix(".txt")


def valid_script_path(path: str) -> bool:
    return bool(SCRIPT_PATH.fullmatch(path)) and not {".", ".."}.intersection(
        path.split("/")
    )


def _title(entry: StoryEntry, rules: StoryRules, group_id: str) -> str | None:
    name = (entry.story_name or "").strip()
    if prefix := rules.act_code.get(group_id):
        return f"{prefix}-ST{entry.story_sort:g} {name}/NBT"
    if not entry.story_code or not entry.avg_tag:
        return None
    code = entry.story_code.strip()
    subpage = rules.avg_tag.get(entry.avg_tag, entry.avg_tag)
    if entry.story_review_type == "SP":
        return f"{code}/{subpage}"
    title = f"{code} {name}".strip() + f"/{subpage}"
    if variation := entry.story_variation:
        title += f"/{variation.id}"
    return title


def _script(
    path: str, title: str, kind: str, group: str, published: dict[str, set[str]]
) -> Script:
    titles = published.get(path, set())
    if len(titles) == 1:
        title = next(iter(titles))
    return Script(path, title, kind, group)


def build_catalog(
    review: StoryReviewTable,
    characters: CharacterTable,
    rules: StoryRules,
    published: dict[str, set[str]],
    complete: set[str],
) -> StoryCatalog:
    char_names = {
        char_id.split("_", 2)[2]: char.name
        for char_id, char in characters.items()
        if char_id.startswith("char_") and char_id.count("_") >= 2 and char.name
    }
    stories: dict[str, Script] = {}
    metadata: dict[str, tuple[str, str]] = {}
    for group_id, group in review.items():
        overrides = {
            story_id: patch.model_dump(by_alias=True, exclude_unset=True)
            for story_id, patch in rules.override.get(group_id, {}).items()
        }
        entries = [
            StoryEntry.model_validate(
                entry.model_dump(by_alias=True)
                | overrides.get(entry.story_id or "", {})
            )
            for entry in group.info_unlock_datas or ()
        ]
        for extra in rules.append.values():
            if extra.story_group != group_id or any(
                entry.story_id == extra.story_id for entry in entries
            ):
                continue
            index = next(
                (
                    i
                    for i, entry in enumerate(entries)
                    if entry.story_sort >= extra.story_sort
                ),
                len(entries),
            )
            entries.insert(index, extra)
        kind = rules.act_type.get(group.act_type, "")
        group_name = group.name or group_id
        memory = MEMORY_GROUP.fullmatch(group_id)
        for entry in entries:
            path = script_path(entry.story_txt or "")
            if not valid_script_path(path):
                continue
            if memory:
                if entry.story_can_show == -1:
                    continue
                code, index = memory.groups()
                if name := char_names.get(code):
                    subpage = index
                    if len(entries) > 1:
                        subpage += f"-{path.rsplit('_', 1)[-1]}"
                    title = f"{name}/干员密录/{subpage}"
                    stories[path] = _script(path, title, "干员密录", name, published)
                else:
                    logger.warning(f"干员密录找不到干员：{group_id}")
                continue
            if not kind:
                continue
            metadata[path] = (kind, group_name)
            if entry.story_can_show == -1:
                continue
            if naming := _title(entry, rules, group_id):
                story = _script(
                    path,
                    naming,
                    entry.wiki_type or kind,
                    entry.wiki_group or group_name,
                    published,
                )
                stories[path] = story

    for section, groups in rules.navigation.items():
        default_kind = "主线" if section == "main" else "支线"
        for group in groups:
            for row in group.group_datas:
                for entry in row.info_unlock_datas:
                    path = script_path(entry.story_txt or "")
                    if entry.story_can_show == -1 or not valid_script_path(path):
                        continue
                    if title := _title(entry, rules, entry.story_group or ""):
                        kind, group_name = metadata.get(
                            path,
                            (
                                row.story_type or group.story_type or default_kind,
                                row.name,
                            ),
                        )
                        stories[path] = _script(
                            path,
                            title,
                            entry.wiki_type or kind,
                            entry.wiki_group or group_name,
                            published,
                        )

    return StoryCatalog(
        stories,
        {path for path, titles in published.items() if len(titles) > 1},
        complete,
    )


async def _load_catalog(
    wiki: Wiki, review: StoryReviewTable, characters: CharacterTable
) -> StoryCatalog:
    rules_path = get_settings().story_rules_path or RULES_PATH
    rules = StoryRules.model_validate_json(await anyio.Path(rules_path).read_bytes())
    rows = await wiki.cargo_rows(
        "story", "_pageName=title,textPath,storyType,storyGroup", order_by="_pageID,_ID"
    )
    published: dict[str, set[str]] = {}
    complete: set[str] = set()
    for row in rows:
        if path := row.get("textPath"):
            published.setdefault(script_path(path), set()).add(row["title"])
            if row.get("storyType") and row.get("storyGroup"):
                complete.add(row["title"])
    return build_catalog(review, characters, rules, published, complete)


Catalog = Annotated[StoryCatalog, Depends(_load_catalog)]
