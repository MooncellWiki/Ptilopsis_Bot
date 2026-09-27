"""收藏品页面自动更新与维护测试"""

import copy
import socket
from contextlib import nullcontext
from unittest.mock import AsyncMock, Mock
from urllib.parse import parse_qs

import click
import httpx2
import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from ptilopsis import __main__ as cli
from ptilopsis.config import RelicConfig, Settings, config
from ptilopsis.jobs import relic
from ptilopsis.relics.merge import common_call, merge_page
from ptilopsis.relics.source import (
    RelicGlossary,
    RelicTopics,
    build_records,
    render_pages,
)
from ptilopsis.relics.state import atomic_json, load_state, state_lock
from ptilopsis.utils.wiki import Wiki, WikiError

pytestmark = pytest.mark.anyio
API = "https://prts.wiki/api.php"


@pytest.fixture(autouse=True)
async def offline(monkeypatch, anyio_backend):
    def deny(*args, **kwargs):
        raise AssertionError("Network access is forbidden in collectible tests")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(relic.anyio, "sleep", AsyncMock())
    yield


@pytest.fixture
def console():
    messages = []
    sink = relic.logger.add(
        lambda message: messages.append(message.record["message"]),
        filter=lambda record: record["name"] == relic.__name__,
    )
    try:
        yield messages
    finally:
        relic.logger.remove(sink)


def item(key="rogue_1_relic_1", name="测试藏品", usage="原效果", **kwargs):
    return {
        "id": key,
        "key": key,
        "name": name,
        "type": "RELIC",
        "rarity": "NORMAL",
        "iconId": key,
        "usage": usage,
        "description": "原描述",
        "obtainApproach": "在集成战略模式中获得",
        "unlockCondDesc": "专用解锁条件",
        **kwargs,
    }


def source(extra=False, usage="原效果"):
    themes = [{"theme": "旧主题", "value": item(usage=usage)}]
    if extra:
        themes.append(
            {"theme": "新主题", "value": item("rogue_7_relic_1", usage="新主题效果")}
        )
    return {"relic": [{"name": "测试藏品", "value": themes}]}


class FakeWiki:
    api_url = API

    def __init__(self, mode="product"):
        self.mode = mode
        self.pages = {}
        self.edits = []
        self.fail = None
        self.timeout_after_save = False
        self.reads = []

    async def read_revision(self, title):
        self.reads.append(title)
        row = self.pages.get(title, {"text": "", "revid": None})
        return {
            "title": title,
            "exists": title in self.pages,
            "redirect": False,
            "contentmodel": "wikitext",
            "starttimestamp": "2026-09-27T00:00:00Z",
            **row,
        }

    async def edit(self, **kwargs):
        assert self.mode == "product"
        assert kwargs["bot"] is True and kwargs["assert_user"] == "bot"
        assert kwargs["retry_transport"] is False
        self.edits.append(kwargs)
        if self.fail:
            raise self.fail
        title = kwargs["title"]
        rev = self.pages.get(title, {}).get("revid", 0) + 1
        self.pages[title] = {"text": kwargs["text"], "revid": rev}
        if self.timeout_after_save:
            raise TimeoutError("Response lost after server saved")
        result = {"result": "Success", "newrevid": rev}
        if kwargs["createonly"]:
            result["new"] = True
        return {"edit": result}


def common_fields(text):
    return common_call(text).fields()


@pytest.fixture
def wiki():
    return FakeWiki()


@pytest.fixture
def opts(tmp_path):
    return RelicConfig(state_file=tmp_path / "state.json")


async def test_create_update_idempotency_and_manual_prose(wiki, opts):
    await relic.synchronize(wiki, render_pages(source()), opts)
    assert wiki.edits[0]["summary"] == "(Page Upload)"
    assert wiki.edits[0]["createonly"] is True
    assert wiki.edits[0]["baserevid"] is None
    assert "approved" not in opts.state_file.read_text(encoding="utf-8")
    page = wiki.pages["测试藏品"]
    page["text"] = (
        "人工前言\n"
        + page["text"].replace("原效果", "人工效果")
        + "[[分类:人工分类]]\n"
    )
    page["revid"] += 1
    await relic.synchronize(wiki, render_pages(source(extra=True)), opts)
    assert len(wiki.edits) == 2
    assert wiki.edits[1]["summary"] == "(Page Update)"
    assert wiki.edits[1]["nocreate"] is True
    assert wiki.edits[1]["baserevid"] == 2
    text = wiki.pages["测试藏品"]["text"]
    fields = common_fields(text)
    assert fields["效果1"] == "人工效果" and fields["主题2"] == "新主题"
    assert fields["iconId"] == "rogue_7_relic_1"
    assert fields["解锁条件1"] == "专用解锁条件"
    assert text.startswith("人工前言\n") and text.endswith("[[分类:人工分类]]\n")
    await relic.synchronize(wiki, render_pages(source(extra=True)), opts)
    assert len(wiki.edits) == 2


async def test_changed_source_effect_never_blocks_new_theme_or_overwrites_old_effect(
    wiki, opts
):
    await relic.synchronize(wiki, render_pages(source()), opts)
    wiki.pages["测试藏品"]["text"] = wiki.pages["测试藏品"]["text"].replace(
        "原效果", "人工效果"
    )
    await relic.synchronize(
        wiki, render_pages(source(extra=True, usage="新数据效果")), opts
    )
    fields = common_fields(wiki.pages["测试藏品"]["text"])
    assert fields["效果1"] == "人工效果" and fields["主题2"] == "新主题"
    assert len(wiki.edits) == 2


async def test_unknown_existing_page_refreshes_headers_but_freezes_old_theme(
    wiki, opts
):
    wiki.pages["测试藏品"] = {
        "text": render_pages(source())[0]["text"].replace("原效果", "人工效果"),
        "revid": 10,
    }
    await relic.synchronize(wiki, render_pages(source(extra=True)), opts)
    fields = common_fields(wiki.pages["测试藏品"]["text"])
    state = load_state(opts.state_file, API)["pages"]["测试藏品"]["managed"]
    assert fields["iconId"] == "rogue_7_relic_1" and fields["效果1"] == "人工效果"
    assert state["iconId"] == "rogue_7_relic_1" and state["效果2"] == "新主题效果"


async def test_deleted_managed_page_is_not_recreated(wiki, opts):
    await relic.synchronize(wiki, render_pages(source()), opts)
    wiki.pages.clear()
    await relic.synchronize(wiki, render_pages(source()), opts)
    assert len(wiki.edits) == 1


@pytest.mark.parametrize(
    "text,extra",
    [
        ("#REDIRECT [[其他页]]", {"redirect": True}),
        ("{}", {"contentmodel": "json"}),
        ("人工页面，尚无 common 模板", {}),
        ("{{收藏品/common|名称=A|名称=B}}", {}),
    ],
)
async def test_ambiguous_or_non_collectible_pages_are_skipped(wiki, opts, text, extra):
    wiki.pages["测试藏品"] = {"text": text, "revid": 1, **extra}
    await relic.synchronize(wiki, render_pages(source()), opts)
    assert not wiki.edits


async def test_preview_never_calls_edit_or_changes_state(wiki, opts):
    wiki.mode = "dev"
    await relic.synchronize(wiki, render_pages(source()), opts)
    assert not wiki.edits and not opts.state_file.exists()
    wiki.mode = "product"
    await relic.synchronize(wiki, render_pages(source()), opts)
    saved = opts.state_file.read_bytes()
    wiki.mode = "dev"
    await relic.synchronize(wiki, render_pages(source(extra=True)), opts)
    assert opts.state_file.read_bytes() == saved and len(wiki.edits) == 1


async def test_bot_permission_failure_stops_without_fallback(wiki, opts, console):
    wiki.fail = WikiError("assertbotfailed", "No bot right")
    with pytest.raises(WikiError, match="assertbotfailed"):
        await relic.synchronize(wiki, render_pages(source()), opts)
    assert len(wiki.edits) == 1
    state = load_state(opts.state_file, API)
    assert not state["pages"] and not state["pending"]
    assert len(console) == 1
    assert "创建失败【测试藏品】" in console[0]
    assert "assertbotfailed" in console[0] and "No bot right" in console[0]


async def test_server_saved_timeout_is_recovered_without_duplicate_edit(
    wiki, opts, console
):
    wiki.timeout_after_save = True
    with pytest.raises(TimeoutError):
        await relic.synchronize(wiki, render_pages(source()), opts)
    assert "测试藏品" in load_state(opts.state_file, API)["pending"]
    assert "创建结果未确认【测试藏品】" in console[0]
    assert "TimeoutError" in console[0] and "pending" in console[0]
    wiki.timeout_after_save = False
    await relic.synchronize(wiki, render_pages(source()), opts)
    state = load_state(opts.state_file, API)
    assert len(wiki.edits) == 1 and not state["pending"]
    assert state["pages"]["测试藏品"]["revid"] == 1
    await relic.synchronize(wiki, render_pages(source(extra=True)), opts)
    assert len(wiki.edits) == 2


async def test_timeout_before_save_rechecks_before_next_run(wiki, opts):
    wiki.fail = TimeoutError()
    with pytest.raises(TimeoutError):
        await relic.synchronize(wiki, render_pages(source()), opts)
    assert len(wiki.edits) == 1
    wiki.fail = None
    await relic.synchronize(wiki, render_pages(source()), opts)
    assert len(wiki.reads) == 2 and len(wiki.edits) == 2
    assert not load_state(opts.state_file, API)["pending"]


async def test_uncertain_write_with_subsequent_human_edit_is_held(wiki, opts):
    wiki.timeout_after_save = True
    with pytest.raises(TimeoutError):
        await relic.synchronize(wiki, render_pages(source()), opts)
    wiki.pages["测试藏品"]["text"] += "人工内容"
    wiki.pages["测试藏品"]["revid"] += 1
    await relic.synchronize(wiki, render_pages(source()), opts)
    assert len(wiki.edits) == 1
    assert "测试藏品" in load_state(opts.state_file, API)["pending"]


async def test_edit_conflict_does_not_advance_baseline_and_requires_next_run(
    wiki, opts, console
):
    await relic.synchronize(wiki, render_pages(source()), opts)
    before = opts.state_file.read_bytes()
    wiki.fail = WikiError("editconflict", "Page changed")
    with pytest.raises(RuntimeError, match="并发编辑"):
        await relic.synchronize(wiki, render_pages(source(extra=True)), opts)
    assert opts.state_file.read_bytes() == before and len(wiki.edits) == 2
    assert len(console) == 1
    assert "维护失败【测试藏品】" in console[0] and "editconflict" in console[0]


async def test_legacy_state_works_without_manifest(wiki, opts):
    text = render_pages(source())[0]["text"]
    wiki.pages["测试藏品"] = {"text": text, "revid": 50}
    atomic_json(
        opts.state_file,
        {
            "schema": "prts-relic-state/v1",
            "pages": {"测试藏品": {"managed": common_fields(text), "revid": 50}},
        },
    )
    await relic.synchronize(wiki, render_pages(source(extra=True)), opts)
    assert common_fields(wiki.pages["测试藏品"]["text"])["iconId"] == "rogue_7_relic_1"


async def test_job_local_source_does_not_download_gamedata(opts, wiki, tmp_path):
    opts.source_file = tmp_path / "relic.json"
    atomic_json(opts.source_file, source())
    wiki.mode = "dev"
    data = AsyncMock()
    await relic.run.func(wiki, data, config.model_copy(update={"relic": opts}))
    data.get.assert_not_called()


async def test_job_native_source_fetches_tables_before_any_write(wiki, opts):
    wiki.mode = "dev"
    data = AsyncMock()
    data.get.side_effect = [topic_fixture(), {"termDescriptionDict": {}}]
    await relic.run.func(wiki, data, config.model_copy(update={"relic": opts}))
    assert [call.args[0] for call in data.get.call_args_list] == [
        "excel/roguelike_topic_table.json",
        "excel/gamedata_const.json",
    ]
    assert wiki.reads == ["测试藏品"] and not wiki.edits
    assert all(call.kwargs == {"region": "CN"} for call in data.get.call_args_list)
    data.get.side_effect = [{"topics": {}, "details": {}}, {"termDescriptionDict": {}}]
    with pytest.raises(ValueError, match="非空"):
        await relic.run.func(wiki, data, config.model_copy(update={"relic": opts}))
    assert wiki.reads == ["测试藏品"]


async def test_unconfirmed_response_stops_remaining_pages(wiki, opts, console):
    wiki.edit = AsyncMock(return_value={"edit": {"result": "Failure", "captcha": {}}})
    draft = source()
    another = copy.deepcopy(draft["relic"][0])
    another["name"] = "第二件藏品"
    draft["relic"].append(another)
    with pytest.raises(RuntimeError, match="未确认"):
        await relic.synchronize(wiki, render_pages(draft), opts)
    wiki.edit.assert_awaited_once()
    assert wiki.reads == ["测试藏品"]
    assert not load_state(opts.state_file, API)["pages"]
    assert len(console) == 2
    assert "结果未确认【测试藏品】" in console[0] and "API 未确认" in console[0]
    assert "未处理【第二件藏品】" in console[1] and "尚未尝试此页" in console[1]


async def test_create_race_keeps_baseline_empty_and_is_not_retried(wiki, opts, console):
    wiki.edit = AsyncMock(return_value=None)
    with pytest.raises(RuntimeError, match="并发编辑"):
        await relic.synchronize(wiki, render_pages(source()), opts)
    wiki.edit.assert_awaited_once()
    state = load_state(opts.state_file, API)
    assert not state["pages"] and not state["pending"]
    assert len(console) == 1
    assert "创建未完成【测试藏品】" in console[0] and "已被其他编辑者创建" in console[0]


def topic_fixture():
    leaves = {
        "rogue_7_relic_1" + suffix: item(
            "rogue_7_relic_1" + suffix,
            name="测试藏品" + name,
            usage=f"效果{level}【测试术语】",
            description=f"描述{level}",
        )
        for suffix, name, level in [
            ("", "", 0),
            ("_a", "α", 3),
            ("_b", "β", 6),
            ("_c", "γ", 9),
        ]
    }
    members = [
        {"relicId": key, "equivalentGrade": level}
        for key, level in zip(leaves, [0, 3, 6, 9], strict=True)
    ]
    return {
        "topics": {"rogue_7": {"name": "未来主题", "sort": 7}},
        "details": {
            "rogue_7": {
                "items": leaves,
                "difficultyUpgradeRelicGroups": {"group": {"relicData": members[::-1]}},
            }
        },
    }


def test_native_source_uses_group_thresholds_merges_descriptions_and_plain_names():
    records = build_records(
        RelicTopics.model_validate(topic_fixture()),
        RelicGlossary.model_validate(
            {
                "termDescriptionDict": {
                    "term": {"termName": "测试术语", "description": "术语说明"}
                }
            }
        ),
    )
    fields = common_fields(render_pages(records)[0]["text"])
    assert fields["主题1"] == "未来主题" and "主题7" not in fields
    assert fields["iconId"] == "rogue_7_relic_1"
    assert fields["效果1"].count("{{color|#d800db|难度") == 4
    for threshold in [0, 3, 6, 9]:
        assert f"难度{threshold}及以上生效：" in fields["效果1"]
        assert f"描述{threshold}" in fields["描述"]
    assert "术语说明" in fields["描述"]


def test_native_kv_arrays_match_dictionary_form():
    raw = topic_fixture()
    data = copy.deepcopy(raw)
    detail = data["details"]["rogue_7"]
    for key in ["items", "difficultyUpgradeRelicGroups"]:
        detail[key] = [{"key": k, "value": v} for k, v in detail[key].items()]
    for key in ["topics", "details"]:
        data[key] = [{"key": k, "value": v} for k, v in data[key].items()]
    assert RelicTopics.model_validate(data) == RelicTopics.model_validate(raw)


def test_unknown_difficulty_and_unrelated_same_name_are_rejected():
    raw = topic_fixture()
    raw["details"]["rogue_7"]["difficultyUpgradeRelicGroups"]["group"]["relicData"][0][
        "equivalentGrade"
    ] = 12
    with pytest.raises(ValueError, match="阈值"):
        build_records(
            RelicTopics.model_validate(raw), RelicGlossary(term_description_dict={})
        )


def test_state_lock_and_site_validation(tmp_path):
    path = tmp_path / "state.json"
    with state_lock(path), pytest.raises(ValueError, match="锁"):
        with state_lock(path):
            pass
    atomic_json(
        path,
        {
            "schema": "prts-relic-state/v1",
            "api_url": "https://other.example/api.php",
            "pages": {},
        },
    )
    with pytest.raises(ValueError, match="另一个"):
        load_state(path, API)


def test_historical_themes_numbering_and_human_deletion():
    old = "{{收藏品/common|主题3=旧主题|效果3=旧效果|主题6=新主题|效果6=新效果}}"
    current = old.replace("|效果3=旧效果", "")
    desired = "{{收藏品/common|主题1=新主题|效果1=新效果}}"
    result = merge_page(current, desired, common_fields(old))
    assert not result["conflicts"]
    fields = common_fields(result["text"])
    assert fields["主题1"] == "旧主题" and fields["主题2"] == "新主题"
    assert "效果1" not in fields and fields["效果2"] == "新效果"


def test_empty_or_duplicate_source_rejected():
    with pytest.raises(ValueError):
        render_pages({"relic": []})
    records = source()
    records["relic"] *= 2
    with pytest.raises(ValueError, match="重复"):
        render_pages(records)


@pytest.mark.parametrize("tracked", [True, False])
async def test_major_theme_update_and_new_page_in_one_automatic_run(
    wiki, opts, tracked
):
    old = render_pages(source())[0]
    if tracked:
        await relic.synchronize(wiki, [old], opts)
    else:
        wiki.pages[old["title"]] = {"text": old["text"], "revid": 1}
    text = wiki.pages[old["title"]]["text"]
    # A blank parameter also belongs to the existing theme and remains blank.
    text = text.replace("|主题1=旧主题", "|主题1='''[[旧主题|人工显示名]]'''")
    text = text.replace("|角标1=", "|角标1=人工角标{{模板|值}}")
    text = text.replace("|售价1=8", "|售价1=人工价格")
    text = "人工导语\n" + text + "[[分类:人工维护]]\n"
    wiki.pages[old["title"]]["text"] = text
    existing = common_fields(text)

    incoming = source(extra=True, usage="游戏修改了旧效果")
    first, latest = incoming["relic"][0]["value"]
    first["value"].update(
        rarity="RARE", unlockCondDesc="新版旧解锁", obtainApproach="新版旧获取"
    )
    latest["value"].update(
        rarity="SUPER_RARE",
        description="新主题完整描述",
        unlockCondDesc="新主题解锁",
        obtainApproach="新主题获取",
    )
    incoming["relic"].append(
        {
            "name": "新收藏品",
            "value": [
                {
                    "theme": "新主题",
                    "value": item("rogue_7_relic_2", name="新收藏品", usage="新品效果"),
                }
            ],
        }
    )
    edits_before = len(wiki.edits)
    await relic.synchronize(wiki, render_pages(incoming), opts)
    after_text = wiki.pages[old["title"]]["text"]
    after = common_fields(after_text)
    for name, value in existing.items():
        if name not in {"iconId", "稀有度", "描述"}:
            assert after[name] == value
    assert after["iconId"] == "rogue_7_relic_1"
    assert after["稀有度"] == "2" and after["描述"] == "新主题完整描述"
    assert after["主题2"] == "新主题" and after["效果2"] == "新主题效果"
    assert after["解锁条件2"] == "新主题解锁" and after["获取条件2"] == "新主题获取"
    assert after_text.startswith("人工导语\n") and after_text.endswith(
        "[[分类:人工维护]]\n"
    )
    new_fields = common_fields(wiki.pages["新收藏品"]["text"])
    assert new_fields["主题1"] == "新主题" and "主题2" not in new_fields
    assert new_fields["效果1"] == "新品效果"
    assert [edit["summary"] for edit in wiki.edits[edits_before:]] == [
        "(Page Update)",
        "(Page Upload)",
    ]
    await relic.synchronize(wiki, render_pages(incoming), opts)
    assert len(wiki.edits) == edits_before + 2


async def test_bot_owned_existing_theme_fields_are_frozen_on_source_change(wiki, opts):
    await relic.synchronize(wiki, render_pages(source()), opts)
    before = common_fields(wiki.pages["测试藏品"]["text"])
    incoming = source(usage="新版效果")
    incoming["relic"][0]["value"][0]["value"].update(
        rarity="SUPER_RARE",
        description="新版描述",
        unlockCondDesc="新版解锁",
        obtainApproach="新版获取",
    )
    await relic.synchronize(wiki, render_pages(incoming), opts)
    after = common_fields(wiki.pages["测试藏品"]["text"])
    assert after["描述"] == "新版描述" and after["稀有度"] == "2"
    assert {
        key: value
        for key, value in after.items()
        if key not in {"iconId", "稀有度", "描述"}
    } == {
        key: value
        for key, value in before.items()
        if key not in {"iconId", "稀有度", "描述"}
    }


@pytest.mark.parametrize("tracking", ["new", "legacy", "none"])
async def test_older_source_cannot_roll_back_latest_headers(
    wiki, opts, tracking, console
):
    page = render_pages(source(extra=True))[0]
    if tracking != "none":
        await relic.synchronize(wiki, [page], opts)
        if tracking == "legacy":
            state = load_state(opts.state_file, API)
            state["pages"][page["title"]].pop("latest_theme")
            atomic_json(opts.state_file, state)
        # Even if a human changed the icon, the saved theme protects against rollback.
        wiki.pages[page["title"]]["text"] = wiki.pages[page["title"]]["text"].replace(
            "|iconId=rogue_7_relic_1", "|iconId=自定义图标"
        )
    else:
        wiki.pages[page["title"]] = {"text": page["text"], "revid": 1}
    before = wiki.pages[page["title"]]["text"]
    count = len(wiki.edits)
    await relic.synchronize(wiki, render_pages(source()), opts)
    assert len(console) == 1
    assert "未处理【测试藏品】" in console[0] and "回退" in console[0]
    assert len(wiki.edits) == count and wiki.pages[page["title"]]["text"] == before


def test_deleted_theme_field_is_not_restored_when_source_changes():
    original = render_pages(source())[0]["text"]
    current = original.replace("|效果1=原效果\n", "")
    incoming = render_pages(source(extra=True, usage="新游戏效果"))[0]["text"]
    result = merge_page(current, incoming, common_fields(original))
    assert not result["conflicts"]
    fields = common_fields(result["text"])
    assert "效果1" not in fields and fields["主题2"] == "新主题"


def scoped_source():
    records = source(extra=True)
    records["relic"][0]["value"].insert(
        1, {"theme": "中间主题", "value": item("rogue_3_relic_1", usage="中间效果")}
    )
    records["relic"][0]["value"][-1]["value"].update(
        rarity="SUPER_RARE", description="最新描述"
    )
    for number, theme, name in [
        (1, "旧主题", "旧主题独有"),
        (7, "新主题", "新主题独有"),
    ]:
        records["relic"].append(
            {
                "name": name,
                "value": [
                    {
                        "theme": theme,
                        "value": item(f"rogue_{number}_relic_2", name=name),
                    }
                ],
            }
        )
    return records


@pytest.mark.parametrize("themes", [[0], [-1], [True], ["6"], [1.5]])
def test_theme_config_rejects_invalid_numbers(themes):
    with pytest.raises(ValidationError):
        RelicConfig(themes=themes)


def test_theme_selection_uses_source_ids_deduplicates_and_numbers_from_one():
    records = scoped_source()
    assert render_pages(records, []) == render_pages(records)
    pages = render_pages(records, [7, 3, 7])
    assert [page["title"] for page in pages] == ["测试藏品", "新主题独有"]
    fields = common_fields(pages[0]["text"])
    assert fields["主题1"] == "中间主题" and fields["主题2"] == "新主题"
    assert "主题3" not in fields and "主题7" not in fields
    assert pages[0]["latest_theme"] == 7
    assert pages[0]["theme_order"] == ["旧主题", "中间主题", "新主题"]


@pytest.mark.parametrize("local_source", [False, True])
async def test_selected_job_rejects_missing_theme_before_reading_any_page(
    wiki, opts, tmp_path, local_source
):
    data = AsyncMock()
    opts.themes = [1 if local_source else 7, 999]
    if local_source:
        opts.source_file = tmp_path / "source.json"
        atomic_json(opts.source_file, source())
    else:
        data.get.side_effect = [topic_fixture(), {"termDescriptionDict": {}}]
    with pytest.raises(ValueError, match="不存在指定主题编号：999"):
        await relic.run.func(wiki, data, config.model_copy(update={"relic": opts}))
    assert not wiki.reads and not wiki.edits and not opts.state_file.exists()


async def test_selected_job_only_reads_matching_pages_without_reports(
    wiki, opts, tmp_path, console
):
    data = AsyncMock()
    opts.source_file = tmp_path / "source.json"
    opts.themes = [7]
    atomic_json(opts.source_file, scoped_source())
    await relic.run.func(wiki, data, config.model_copy(update={"relic": opts}))
    assert wiki.reads == ["测试藏品", "新主题独有"]
    assert "旧主题独有" not in wiki.pages
    for row in wiki.pages.values():
        fields = common_fields(row["text"])
        assert fields["主题1"] == "新主题" and "主题2" not in fields
    assert len(wiki.edits) == 2 and not console
    assert {path.name for path in tmp_path.iterdir()} == {"source.json", "state.json"}
    data.get.assert_not_called()


@pytest.mark.parametrize("tracked", [True, False])
async def test_selected_older_theme_backfills_in_order_without_touching_other_themes(
    wiki, opts, tracked
):
    records = scoped_source()
    draft = render_pages(records, [7])[0]
    if tracked:
        await relic.synchronize(wiki, [draft], opts)
    else:
        wiki.pages[draft["title"]] = {"text": draft["text"], "revid": 1}
    wiki.pages[draft["title"]]["text"] = (
        "人工导语\n"
        + wiki.pages[draft["title"]]["text"]
        .replace("|效果1=新主题效果", "|效果1=人工效果")
        .replace("|角标1=", "|角标1={{人工角标}}")
        .replace("|解锁条件1=专用解锁条件\n", "")
        + "[[分类:人工维护]]\n"
    )
    before = common_fields(wiki.pages[draft["title"]]["text"])
    older = render_pages(records, [1])[0]
    opts.themes = [1]
    await relic.synchronize(wiki, [older], opts)
    after_text = wiki.pages[draft["title"]]["text"]
    after = common_fields(after_text)
    assert after["主题1"] == "旧主题" and after["主题2"] == "新主题"
    assert "主题3" not in after and "中间主题" not in after_text
    for prefix in ["主题", "角标", "售价", "效果", "获取条件"]:
        assert after[prefix + "2"] == before[prefix + "1"]
    assert "解锁条件2" not in after
    assert after["iconId"] == "rogue_7_relic_1"
    assert after["稀有度"] == "2" and after["描述"] == "最新描述"
    assert after_text.startswith("人工导语\n") and after_text.endswith(
        "[[分类:人工维护]]\n"
    )
    state = load_state(opts.state_file, API)
    assert state["pages"][draft["title"]]["latest_theme"] == 7
    count = len(wiki.edits)
    await relic.synchronize(wiki, [older], opts)
    assert len(wiki.edits) == count

    # Full maintenance later adds the omitted middle theme, keeping manual values.
    opts.themes = []
    await relic.synchronize(wiki, [render_pages(records)[0]], opts)
    full = common_fields(wiki.pages[draft["title"]]["text"])
    assert [full[f"主题{i}"] for i in (1, 2, 3)] == ["旧主题", "中间主题", "新主题"]
    assert full["效果3"] == "人工效果" and full["角标3"] == "{{人工角标}}"
    if tracked:
        assert "解锁条件3" not in full


async def test_selected_update_does_not_fill_missing_unselected_fields(wiki, opts):
    records = scoped_source()
    page = render_pages(records)[0]
    wiki.pages[page["title"]] = {
        "text": page["text"].replace("|获取条件2=\n", "").replace("|获取条件3=\n", ""),
        "revid": 1,
    }
    await relic.synchronize(wiki, [render_pages(records, [3])[0]], opts)
    after = common_fields(wiki.pages[page["title"]]["text"])
    assert after["获取条件2"] == "" and "获取条件3" not in after


@pytest.mark.parametrize("mode", ["dev", "product"])
async def test_only_problems_are_printed_and_no_page_artifacts_are_written(
    wiki, tmp_path, monkeypatch, console, mode
):
    monkeypatch.chdir(tmp_path)
    opts = RelicConfig.model_validate(
        {
            "stateFile": str(tmp_path / "state.json"),
            "reportDir": str(tmp_path / "retired-reports"),
        }
    )
    assert "report_dir" not in opts.model_dump()
    wiki.mode = mode
    await relic.synchronize(wiki, render_pages(source()), opts)
    await relic.synchronize(wiki, render_pages(source()), opts)
    assert not console
    wiki.pages["测试藏品"] = {"text": "#重定向 [[目标]]", "revid": 2}
    await relic.synchronize(wiki, render_pages(source()), opts)
    assert len(console) == 1 and "测试藏品" in console[0] and "重定向" in console[0]
    if mode == "dev":
        assert "预检未通过" in console[0] and not wiki.edits
        assert not list(tmp_path.iterdir())
    else:
        assert "未处理" in console[0]
        assert {path.name for path in tmp_path.iterdir()} == {"state.json"}
    assert not any("{{收藏品/common" in message for message in console)


@pytest.mark.parametrize("mode", ["dev", "product"])
async def test_failed_read_prints_page_reason_and_unattempted_pages(
    wiki, opts, console, mode
):
    wiki.mode = mode
    wiki.read_revision = AsyncMock(side_effect=TimeoutError("读取超时"))
    drafts = source()
    other = copy.deepcopy(drafts["relic"][0])
    other["name"] = "尚未处理藏品"
    drafts["relic"].append(other)
    with pytest.raises(TimeoutError):
        await relic.synchronize(wiki, render_pages(drafts), opts)
    assert not wiki.edits and not opts.state_file.exists()
    assert len(console) == 2
    assert "测试藏品" in console[0] and "读取超时" in console[0]
    assert "尚未处理藏品" in console[1] and "尚未尝试此页" in console[1]
    if mode == "dev":
        assert "预检未通过" in console[0]


@pytest.mark.parametrize("response_lost", [False, True])
async def test_maintenance_edit_guards_and_no_transport_retry(response_lost):
    posts = []

    def handler(request):
        if request.method == "GET":
            return httpx2.Response(
                200, json={"query": {"tokens": {"csrftoken": "CSRF"}}}
            )
        posts.append(
            {
                key: values[0]
                for key, values in parse_qs(request.content.decode()).items()
            }
        )
        if response_lost:
            raise httpx2.ReadTimeout("Response lost", request=request)
        return httpx2.Response(
            200, json={"edit": {"result": "Success", "newrevid": 124}}
        )

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
        wiki = Wiki(API, client=client)
        expected = pytest.raises(httpx2.ReadTimeout) if response_lost else nullcontext()
        with expected:
            await wiki.edit(
                title="藏品",
                text="源码",
                baserevid=123,
                starttimestamp="2026-09-27T00:00:00Z",
                nocreate=True,
                assert_user="bot",
                maxlag=5,
                watchlist="nochange",
                retry_transport=False,
            )
    assert len(posts) == 1
    sent = posts[0]
    assert sent["assert"] == "bot" and sent["bot"] == "1"
    assert sent["baserevid"] == "123" and sent["nocreate"] == "1"
    assert sent["starttimestamp"] == "2026-09-27T00:00:00Z"
    assert sent["maxlag"] == "5" and sent["watchlist"] == "nochange"
    assert "retry_transport" not in sent and "assert_user" not in sent


@pytest.mark.parametrize(
    "kind", ["existing", "missing", "redirect", "hidden", "invalid", "error"]
)
async def test_revision_snapshot_distinguishes_missing_unreadable_and_redirect(kind):
    def handler(request):
        params = dict(request.url.params)
        assert params["action"] == "query" and params["rvslots"] == "main"
        assert "redirects" not in params
        page = {
            "title": "藏品",
            "contentmodel": "wikitext",
            "revisions": [
                {
                    "revid": 42,
                    "slots": {"main": {"content": "正文", "contentmodel": "wikitext"}},
                }
            ],
        }
        if kind == "missing":
            page = {"title": "藏品", "missing": True}
        elif kind == "redirect":
            page["redirect"] = True
        elif kind == "hidden":
            page["revisions"][0]["slots"]["main"] = {"texthidden": True}
        elif kind == "invalid":
            page = {"title": "藏品", "invalid": True}
        elif kind == "error":
            return httpx2.Response(
                200, json={"error": {"code": "permissiondenied", "info": "no"}}
            )
        return httpx2.Response(
            200,
            json={"curtimestamp": "2026-09-27T00:00:00Z", "query": {"pages": [page]}},
        )

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
        wiki = Wiki(API, client=client)
        if kind in {"hidden", "invalid", "error"}:
            with pytest.raises((ValueError, WikiError)):
                await wiki.read_revision("藏品")
        else:
            row = await wiki.read_revision("藏品")
            assert row["exists"] == (kind != "missing")
            assert row["redirect"] == (kind == "redirect")
            assert row["revid"] == (None if kind == "missing" else 42)


def test_mode_registration_and_help():
    assert "relic.run" in cli.jobs_for(("regular",))
    assert cli.jobs_for(("relic",)) == ["relic.run"]
    assert cli.jobs_for(("regular", "relic")).count("relic.run") == 1
    result = CliRunner().invoke(cli.main, ["--help"])
    assert result.exit_code == 0 and "--relic-source" in result.output
    assert "--relic-theme" in result.output


@pytest.mark.parametrize(
    "themes,modes,dev,failed,commit",
    [
        ([], ("relic",), False, [], True),
        ([], ("relic",), True, [], False),
        ([], ("relic",), False, ["relic.run"], False),
        ([6], ("relic",), False, [], False),
        ([6], ("relic",), True, [], False),
        ([6], ("regular",), False, [], False),
        ([6], ("regular",), True, [], False),
        ([6], ("new",), False, [], True),
        ([6], ("new",), True, [], False),
    ],
)
async def test_cli_version_commit_policy(
    monkeypatch, themes, modes, dev, failed, commit
):
    scoped = config.model_copy(update={"relic": RelicConfig(themes=themes)})
    data = Mock(aclose=AsyncMock())
    data.unpacker.check_update = AsyncMock(return_value=True)
    wiki = Mock(aclose=AsyncMock())
    monkeypatch.setattr(cli, "GameData", Mock(return_value=data))
    monkeypatch.setattr(cli.Wiki, "login", AsyncMock(return_value=wiki))
    monkeypatch.setattr(cli, "discover_jobs", Mock())
    monkeypatch.setattr(cli, "run_jobs", AsyncMock(return_value=failed))
    settings = Settings(_env_file=None, username="dummy", password="dummy")
    expected = (
        pytest.raises(click.ClickException, match="未推进") if failed else nullcontext()
    )
    with expected:
        assert await cli._amain(scoped, settings, "cn", bool(themes), dev, modes) == (
            not dev
        )
    assert data.unpacker.commit_version.call_count == int(commit)
    wiki.aclose.assert_awaited_once()
    data.aclose.assert_awaited_once()


@pytest.mark.parametrize(
    "args,expected",
    [
        ([], [3]),
        (["--relic-theme", "6", "--relic-theme", "1", "--relic-theme", "6"], [1, 6]),
    ],
)
def test_cli_theme_options_override_configuration(monkeypatch, args, expected):
    monkeypatch.setattr(
        cli, "config", config.model_copy(update={"relic": RelicConfig(themes=[3])})
    )
    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: Settings(
            _env_file=None, username="dummy", password="dummy", sentry_dsn=""
        ),
    )
    run = Mock(return_value=False)
    monkeypatch.setattr(cli.anyio, "run", run)
    result = CliRunner().invoke(cli.main, [*args, "relic"])
    assert result.exit_code == 0, result.output
    assert run.call_args.args[1].relic.themes == expected


@pytest.mark.parametrize(
    "args",
    [
        ["--relic-theme", "0", "relic"],
        ["--relic-theme", "-1", "relic"],
        ["--relic-theme", "rogue_6", "relic"],
        ["--relic-theme", "6"],
        ["--relic-theme", "6", "new"],
    ],
)
def test_cli_rejects_invalid_theme_or_wrong_mode_before_network(monkeypatch, args):
    run = Mock(side_effect=AssertionError("Must not start network workflow"))
    monkeypatch.setattr(cli.anyio, "run", run)
    result = CliRunner().invoke(cli.main, args)
    assert result.exit_code == 2
    run.assert_not_called()
