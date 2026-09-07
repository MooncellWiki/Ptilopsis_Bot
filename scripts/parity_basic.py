"""把 basic / char_attr job 生成的页面落盘,供重构前后做 diff。

    uv run python scripts/parity_basic.py out/before
    git switch <branch>
    uv run python scripts/parity_basic.py out/after
    diff -r out/before out/after

不访问 wiki:干员序号表为空,召唤物页面由内存里的假 Wiki 收集。
"""

import json
import sys
from pathlib import Path
from typing import Any

from ptilopsis.jobs import basic, char_attr
from ptilopsis.utils.richTextStyles import RichTextStyles

GAMEDATA = Path("thirdparty/ArknightsGameData/zh_CN/gamedata/excel")


class RecordingWiki:
    """只记录 edit 的页面文本,其余调用为空操作。"""

    def __init__(self) -> None:
        self.pages: dict[str, str] = {}

    def edit(self, title: str | None = None, text: str | None = None, **_: Any):
        if title is not None:
            self.pages[title] = text or ""

    def protect(self, *_: Any, **__: Any) -> None:
        return None


def load(name: str) -> Any:
    return json.loads((GAMEDATA / f"{name}.json").read_text(encoding="utf-8"))


def main(out_dir: Path) -> None:
    character_table = load("character_table")
    uniequip_table = load("uniequip_table")
    battle_equip_table = load("battle_equip_table")
    skill_table = load("skill_table")
    building_data = load("building_data")
    item_table = load("item_table")
    team_table = load("handbook_team_table")
    stories_table = load("handbook_info_table")
    skin_table = load("skin_table")
    gamedata_const = load("gamedata_const")
    charword_table = load("charword_table")
    medal_table = load("medal_table")
    id_table: dict[str, Any] = {}
    rts = RichTextStyles(gamedata_const)
    wiki = RecordingWiki()

    chars_dir = out_dir / "chars"
    chars_dir.mkdir(parents=True, exist_ok=True)
    for char_key, char_detail in character_table.items():
        char_detail["name"] = char_detail["name"].strip()
        if char_detail["profession"] in ("TRAP", "TOKEN"):
            continue
        if char_detail["isNotObtainable"]:
            continue
        stories_list_set, stories_list = basic.get_stories_list(
            char_detail, stories_table, char_key
        )
        page = basic.content.format(
            name=char_detail["name"],
            char_approach=basic.get_char_approach(char_detail, id_table),
            basic_info=basic.get_basic_info(
                char_detail,
                char_key,
                id_table,
                rts,
                uniequip_table,
                team_table,
                skin_table,
                charword_table,
            ),
            phases_data=basic.get_phases_data(
                char_detail, char_key, uniequip_table, battle_equip_table, team_table
            ),
            range_data=basic.get_range_data(char_detail),
            talents=basic.get_talent_list(char_detail, rts),
            potential=basic.get_potential_list(char_detail),
            skill=basic.get_skill_list(char_detail, skill_table, rts),
            building=basic.get_building_skill(building_data, char_key, rts),
            token_info=basic.get_token_info(
                wiki, char_detail, False, character_table, skill_table, rts
            ),
            phase=basic.get_phase_list(char_detail, gamedata_const, item_table),
            skill_levelup=basic.get_skill_levelUp_list(
                char_detail, item_table, skill_table
            ),
            equip="".join(
                basic.get_battle_equip(
                    char_detail,
                    char_key,
                    battle_equip_table,
                    uniequip_table,
                    item_table,
                    rts,
                )
            ),
            related_item=basic.get_related_item(char_detail, item_table),
            stories=stories_list_set + stories_list,
            handbook_avg=basic.get_handbook_avg(
                char_detail, stories_table, char_key, medal_table
            ),
            handbook_stage=basic.get_handbook_stage(
                char_detail, char_key, stories_table, item_table, rts
            ),
        )
        (chars_dir / f"{char_key}.wiki").write_text(page, encoding="utf-8")

    tokens_dir = out_dir / "tokens"
    tokens_dir.mkdir(parents=True, exist_ok=True)
    for title, text in wiki.pages.items():
        (tokens_dir / f"{title.replace('/', '_')}.wiki").write_text(
            text, encoding="utf-8"
        )

    (out_dir / "char_attr.wiki").write_text(
        char_attr.get_char_attr(character_table, uniequip_table, id_table, rts),
        encoding="utf-8",
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
