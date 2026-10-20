import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from ptilopsis.gamedata.building_data import BuildingData
from ptilopsis.jobs.building_buff import get_building_buff, run
from ptilopsis.jobs.params import RichText
from ptilopsis.log import logger
from ptilopsis.utils.wiki import Wiki

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "building_buff"
GOLDEN_DIR = Path(__file__).parent / "golden" / "building_buff"


def stub_compile_rich_text(text: str | None) -> str:
    return f"[RTS]{text}"


def building_data() -> BuildingData:
    fixture = json.loads((FIXTURE_DIR / "basic.json").read_text(encoding="utf-8"))
    return BuildingData.model_validate(fixture)


def test_building_buff_rendering_matches_golden() -> None:
    # 覆盖技能名消歧、同名去重、空房间跳过,每页只有一个技能模板。
    actual = get_building_buff(building_data(), stub_compile_rich_text)
    expected = {
        f"后勤技能一览/{path.stem}": path.read_text(encoding="utf-8")
        for path in GOLDEN_DIR.glob("*.wiki")
    }
    assert actual == expected


@pytest.mark.anyio
async def test_job_creates_updates_and_skips_individual_pages() -> None:
    data = building_data()
    pages = get_building_buff(data, stub_compile_rich_text)
    unchanged = "后勤技能一览/领袖(控制中枢)"
    changed = "后勤技能一览/普通技能"
    created = "后勤技能一览/领袖(宿舍)"
    wiki = Mock(spec=Wiki)
    wiki.read_many = AsyncMock(
        return_value={unchanged: pages[unchanged], changed: "旧技能内容"}
    )
    wiki.edit = AsyncMock()
    rts = Mock(spec=RichText)
    rts.compile.side_effect = stub_compile_rich_text

    await run.func(wiki, data, rts)

    assert list(wiki.read_many.call_args.args[0]) == list(pages)
    edits = {
        call.kwargs["title"]: call.kwargs["text"] for call in wiki.edit.call_args_list
    }
    assert edits == {changed: pages[changed], created: pages[created]}


@pytest.mark.anyio
async def test_empty_data_does_not_write() -> None:
    wiki = Mock(spec=Wiki)
    wiki.read_many = AsyncMock(return_value={})
    wiki.edit = AsyncMock()
    await run.func(wiki, BuildingData(), Mock(spec=RichText))
    wiki.edit.assert_not_called()


def test_cross_room_duplicate_name_warns() -> None:
    # 页面按技能名区分,跨房间同名只保留首条并提醒补消歧名
    data = BuildingData.model_validate(
        {
            "rooms": {"MANUFACTURE": {"name": "制造站"}, "TRADING": {"name": "贸易站"}},
            "buffs": {
                "manu": {
                    "buffId": "manu",
                    "buffName": "同名技能",
                    "roomType": "MANUFACTURE",
                },
                "trade": {
                    "buffId": "trade",
                    "buffName": "同名技能",
                    "roomType": "TRADING",
                },
            },
        }
    )
    captured: list[str] = []
    sink = logger.add(captured.append, level="WARNING", format="{message}")
    try:
        pages = get_building_buff(data, stub_compile_rich_text)
    finally:
        logger.remove(sink)

    assert list(pages) == ["后勤技能一览/同名技能"]
    assert "|房间=制造站" in pages["后勤技能一览/同名技能"]
    assert len(captured) == 1
    assert "trade" in captured[0]
