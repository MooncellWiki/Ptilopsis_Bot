import json
from pathlib import Path

from ptilopsis.gamedata.building_data import BuildingData
from ptilopsis.jobs.building_buff import get_building_buff

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "building_buff"
GOLDEN_DIR = Path(__file__).parent / "golden" / "building_buff"


def stub_compile_rich_text(text: str | None) -> str:
    return f"[RTS]{text}"


def test_building_buff_rendering_matches_golden() -> None:
    # 夹具覆盖技能名覆盖、同房间同名技能去重、空房间跳过
    fixture = json.loads((FIXTURE_DIR / "basic.json").read_text(encoding="utf-8"))

    actual = get_building_buff(
        BuildingData.model_validate(fixture), stub_compile_rich_text
    )
    expected = (GOLDEN_DIR / "basic.wiki").read_text(encoding="utf-8")

    assert actual == expected
