from collections.abc import Iterable
from dataclasses import replace

import pytest

from ptilopsis.gamedata.character_table import CharacterData
from ptilopsis.gamedata.story_review_table import StoryReviewTable
from ptilopsis.jobs._story_catalog import RULES_PATH, Script, StoryRules, build_catalog
from ptilopsis.jobs._story_wikitext import (
    DATA_REFERENCE,
    add_stage_links,
    add_story_fields,
    render_story,
)
from ptilopsis.jobs.story import _sync_story, _sync_widget
from ptilopsis.utils.wiki import PageRevision, Wiki


def test_catalog_uses_live_title_review_metadata_and_manual_navigation() -> None:
    rules = StoryRules.model_validate_json(RULES_PATH.read_bytes())
    variation = "obt/main/level_main_15-15_end_variation01"
    renamed = "obt/main/level_main_06-14_beg"
    review = StoryReviewTable.validate_python(
        {
            "main_15": {
                "name": "离解复合",
                "actType": "MAIN_STORY",
                "infoUnlockDatas": [
                    {
                        "storyId": "main_15_level_main_15-15_end_variation01",
                        "storyCode": "15-17",
                        "storyName": "“她”",
                        "avgTag": "幕间",
                        "storyTxt": variation,
                    }
                ],
            },
            "main_6": {
                "name": "局部坏死",
                "actType": "MAIN_STORY",
                "infoUnlockDatas": [
                    {
                        "storyCode": "6-16",
                        "storyName": "黑兔子,白兔子",
                        "avgTag": "行动前",
                        "storyTxt": renamed,
                    }
                ],
            },
            "story_otter_set_1": {
                "infoUnlockDatas": [
                    {"storyTxt": "obt/memory/story_otter_1_1"},
                    {"storyTxt": "obt/memory/story_otter_1_2"},
                ],
            },
        }
    )
    catalog = build_catalog(
        review,
        {"char_242_otter": CharacterData(name="梅尔")},
        rules,
        {renamed: {"6-16 黑兔子，白兔子/BEG"}},
        set(),
    )
    story = catalog.stories[variation]
    assert story.title == "15-17 “她”/END/SP1"
    assert story.group == "离解复合"
    assert catalog.stories[renamed].label == "6-16 黑兔子，白兔子 行动前"
    assert catalog.stories["obt/memory/story_otter_1_2"].title == "梅尔/干员密录/1-2"
    ending = catalog.stories["obt/roguelike/ro6/level_rogue6_ending_4"]
    assert (ending.title, ending.label, ending.kind) == (
        "RO6-END-4/NBT",
        "旧日重燃",
        "剧情",
    )
    assert "obt/roguelike/ro6/level_rogue6_ending_5" not in catalog.stories


STORY = Script(
    "obt/main/level_main_00-01_beg",
    "0-1 坍塌/BEG",
    "0-1 坍塌 行动前",
    "主线",
    "黑暗时代·上",
)


def test_backfill_only_touches_empty_fields_on_the_simulator_call() -> None:
    original = (
        "手工序言\n{{剧情模拟器\n"
        "|音频数据={{Widget:Data_Audio}}\n|剧情类型=\n|剧情分组=人工分组\n"
        "|文本数据=\n[Dialog]\n}}\n{{剧情导航}}\n手工附注"
    )
    updated = add_story_fields(original, STORY)
    assert updated is not None
    assert "|文本路径=obt/main/level_main_00-01_beg" in updated
    assert "|剧情类型=主线\n|剧情分组=人工分组" in updated
    assert updated.startswith("手工序言\n")
    assert updated.endswith("|文本数据=\n[Dialog]\n}}\n{{剧情导航}}\n手工附注")
    assert add_story_fields(updated, STORY) == updated
    assert add_story_fields(updated, replace(STORY, path="obt/main/other")) is None


class CaptureWiki(Wiki):
    def __init__(self, *pages: PageRevision) -> None:
        self.pages = {page.title: page for page in pages}
        self.edits = []
        self.mode = "product"

    async def read_revisions(self, titles: Iterable[str]) -> dict[str, PageRevision]:
        return {title: self.pages[title] for title in titles if title in self.pages}

    async def edit(self, **kwargs):
        self.edits.append(kwargs)
        return {"edit": {"result": "Success"}}


def revision(title: str, text: str, contentmodel: str = "wikitext") -> PageRevision:
    return PageRevision(title, text, 123, "base", "start", False, contentmodel)


@pytest.mark.anyio
async def test_story_with_signature_creates_plain_text_before_linking() -> None:
    wiki = CaptureWiki()
    await _sync_story(wiki, STORY, None, "[Dialog]\n~~~~")
    data, parent = wiki.edits
    assert (data["title"], data["contentmodel"], data["text"]) == (
        f"{STORY.title}/data",
        "text",
        "[Dialog]\n~~~~",
    )
    assert data["createonly"] and parent["createonly"]
    assert DATA_REFERENCE in parent["text"]


@pytest.mark.anyio
async def test_explicit_script_refresh_preserves_manual_wikitext_and_data_model() -> (
    None
):
    original = render_story(STORY, "unused", subpage=True)
    parent = revision(STORY.title, f"手工前言\n{original}\n手工附注")
    data = revision(f"{STORY.title}/data", "[Dialog]\n~~~~", "text")
    wiki = CaptureWiki(parent, data)
    await _sync_story(wiki, STORY, parent, "[Dialog]\n屏幕上有一行字")
    [edit] = wiki.edits
    assert edit["title"] == data.title and edit["baserevid"] == data.revid
    assert edit["nocreate"] and edit["text"] == "[Dialog]\n屏幕上有一行字"


def test_stage_links_add_to_the_normal_stage_without_replacing_notes() -> None:
    title = "0-1 坍塌"
    normal = "==普通==\n{{普通关卡信息\n|关卡代号=0-1\n}}"
    pair = {"BEG": STORY, "END": replace(STORY, title=f"{title}/END")}
    source = f"{{{{pathnav2|关卡一览}}}}\n{normal}\n==注释与链接==\n手工注释"
    expected = source.replace(normal, "==剧情==\n{{剧情跳转/关卡|0-1|坍塌}}\n" + normal)
    assert add_stage_links(source, title, pair) == expected
    assert add_stage_links(expected, title, pair) == expected
    assert (
        add_stage_links(
            expected.replace("==剧情==\n", "==剧情==\n手工备注\n"), title, pair
        )
        is None
    )


@pytest.mark.anyio
async def test_stale_widget_export_does_not_remove_live_entries() -> None:
    wiki = CaptureWiki(revision("Widget:Data_Audio", '{"old":"a","new":"b"}'))
    await _sync_widget(wiki, "story_variables.json", '{"old":"a"}')
    assert wiki.edits == []

    await _sync_widget(wiki, "story_variables.json", '{"old":"a","new":"b","next":"c"}')
    [edit] = wiki.edits
    assert edit["baserevid"] == 123 and edit["nocreate"]
