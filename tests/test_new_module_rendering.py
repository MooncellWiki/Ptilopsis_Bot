import json
from pathlib import Path

from ptilopsis.jobs.newModule import update_new_module

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "new_module"
GOLDEN_DIR = Path(__file__).parent / "golden" / "new_module"


def test_new_module_rendering_matches_golden() -> None:
    fixture = json.loads((FIXTURE_DIR / "basic.json").read_text(encoding="utf-8"))

    actual = update_new_module(
        fixture["module_table"],
        fixture["character_table"],
        fixture["current_timestamp"],
    )
    # 文本 fixture 以换行结尾,实际 wiki 数据页沿用旧实现、不带行尾换行。
    expected = (
        (GOLDEN_DIR / "basic.wiki").read_text(encoding="utf-8").removesuffix("\n")
    )

    assert actual == expected


def test_new_module_rendering_is_empty_without_tracks() -> None:
    actual = update_new_module(
        {"equipDict": {}, "equipTrackDict": []},
        {},
        current_timestamp=2000000000,
    )

    assert actual == ""
