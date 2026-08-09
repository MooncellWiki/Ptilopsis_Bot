import json
from pathlib import Path

from ptilopsis.jobs.medal import update_medal

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "medal"
GOLDEN_DIR = Path(__file__).parent / "golden" / "medal"


class StubRichTextStyles:
    def compile(self, text: str) -> str:
        return f"[RTS]{text}"


def test_medal_rendering_matches_golden() -> None:
    fixture = json.loads((FIXTURE_DIR / "basic.json").read_text(encoding="utf-8"))

    actual = update_medal(
        fixture["medal_table"],
        fixture["character_table"],
        fixture["building_data"],
        fixture["item_table"],
        StubRichTextStyles(),
    )
    expected = (GOLDEN_DIR / "basic.wiki").read_text(encoding="utf-8")

    assert actual == expected
