import json
from pathlib import Path

import pytest

from ptilopsis.gamedata.item import ItemData
from ptilopsis.jobs.item import classify_item, should_skip_item, update_item

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "item"
GOLDEN_DIR = Path(__file__).parent / "golden" / "item"


@pytest.mark.parametrize("case", ["formulas", "no_obtain"])
def test_item_rendering_matches_golden(case: str) -> None:
    fixture = json.loads((FIXTURE_DIR / f"{case}.json").read_text(encoding="utf-8"))

    actual = update_item(
        fixture["item_key"],
        fixture["item_table"],
        fixture["building_data"],
        fixture["stage_table"],
    )
    # 旧实现拼接出的页面末尾没有换行;golden 文件本身保留常规的 POSIX 行尾。
    expected = (
        (GOLDEN_DIR / f"{case}.wiki").read_text(encoding="utf-8").removesuffix("\n")
    )

    assert actual == expected


@pytest.mark.parametrize(
    ("item_key", "name", "expected"),
    [
        ("token", "测试干员的信物", "信物"),
        ("token", "测试干员的中坚信物", "中坚信物"),
        ("token", "高级资深干员信物", "通用信物"),
        ("321", "术师芯片组", "芯片组"),
        ("322", "术师双芯片", "双芯片"),
        ("323", "术师芯片", "芯片"),
        ("30001", "测试材料", "材料"),
        ("73", "普通道具", "其他道具"),
        ("custom", "活动道具", "其他道具"),
    ],
)
def test_classify_item(item_key: str, name: str, expected: str) -> None:
    assert classify_item(item_key, name) == expected


def test_should_skip_item_preserves_job_filters() -> None:
    base = {
        "itemId": "test_item",
        "name": "测试道具",
        "description": "",
        "rarity": "TIER_1",
        "iconId": "test_item",
        "sortId": 1,
        "usage": "",
        "obtainApproach": "",
        "hideInItemGet": False,
        "itemType": "MATERIAL",
        "buildingProductList": [],
    }

    item = ItemData.model_validate(base)
    assert not should_skip_item(item, set(), set())
    assert should_skip_item(item, {"测试道具"}, set())
    assert should_skip_item(item, set(), {"测试道具"})

    assert should_skip_item(
        ItemData.model_validate({**base, "hideInItemGet": True}), set(), set()
    )
    assert should_skip_item(
        ItemData.model_validate({**base, "itemType": "EMOTICON_SET"}), set(), set()
    )
