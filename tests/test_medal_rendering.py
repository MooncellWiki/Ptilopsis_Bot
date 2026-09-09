import json
from pathlib import Path

import pytest

from ptilopsis.gamedata.building_data import BuildingData
from ptilopsis.gamedata.character_table import CharacterTable
from ptilopsis.gamedata.item_table import InventoryData
from ptilopsis.gamedata.medal_table import MedalData
from ptilopsis.jobs.medal import update_medal

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "medal"
GOLDEN_DIR = Path(__file__).parent / "golden" / "medal"


def stub_compile_rich_text(text: str) -> str:
    return f"[RTS]{text}"


@pytest.mark.parametrize("case", ["basic", "plated_null_get_method"])
def test_medal_rendering_matches_golden(case: str) -> None:
    fixture = json.loads((FIXTURE_DIR / f"{case}.json").read_text(encoding="utf-8"))

    # 夹具是原始 JSON,和 job 运行时一样先校验成模型再渲染
    actual = update_medal(
        MedalData.model_validate(fixture["medal_table"]),
        CharacterTable.validate_python(fixture["character_table"]),
        BuildingData.model_validate(fixture["building_data"]),
        InventoryData.model_validate(fixture["item_table"]),
        stub_compile_rich_text,
    )
    expected = (GOLDEN_DIR / f"{case}.wiki").read_text(encoding="utf-8")

    assert actual == expected
