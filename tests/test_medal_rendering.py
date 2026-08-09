import json
from pathlib import Path

import pytest

from ptilopsis.jobs.medal import update_medal

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "medal"
GOLDEN_DIR = Path(__file__).parent / "golden" / "medal"


class StubRichTextStyles:
    def compile(self, text: str) -> str:
        return f"[RTS]{text}"


@pytest.mark.parametrize("case", ["basic", "plated_null_get_method"])
def test_medal_rendering_matches_golden(case: str) -> None:
    fixture = json.loads((FIXTURE_DIR / f"{case}.json").read_text(encoding="utf-8"))

    actual = update_medal(
        fixture["medal_table"],
        fixture["character_table"],
        fixture["building_data"],
        fixture["item_table"],
        StubRichTextStyles(),
    )
    expected = (GOLDEN_DIR / f"{case}.wiki").read_text(encoding="utf-8")

    assert actual == expected
