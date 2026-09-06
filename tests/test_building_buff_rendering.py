import json
from pathlib import Path

from ptilopsis.jobs.building_buff import get_building_buff

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "building_buff"
GOLDEN_DIR = Path(__file__).parent / "golden" / "building_buff"


def stub_compile_rich_text(text: str) -> str:
    return f"[RTS]{text}"


def test_building_buff_rendering_matches_golden() -> None:
    fixture = json.loads((FIXTURE_DIR / "basic.json").read_text(encoding="utf-8"))

    actual = get_building_buff(fixture, stub_compile_rich_text)
    expected = (GOLDEN_DIR / "basic.wiki").read_text(encoding="utf-8")

    assert actual == expected
