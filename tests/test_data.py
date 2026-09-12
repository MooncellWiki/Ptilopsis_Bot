"""GameData:国服走 torappu(带缓存),海外服走子模块目录。"""

import json
from pathlib import Path
from typing import Any

import pytest

from ptilopsis.config import Config
from ptilopsis.utils.data import GameData

CN_VERSION = "26-09-03-04-06-00_ed95a2"


class FakeTorappu:
    def __init__(self, files: dict[tuple[str, str], bytes]) -> None:
        self.files = files
        self.fetches: list[tuple[str, str]] = []

    def fetch(self, res_version: str, path: str) -> bytes:
        self.fetches.append((res_version, path))
        try:
            return self.files[(res_version, path)]
        except KeyError:
            raise FileNotFoundError(path) from None

    def walk(self, res_version: str, path: str):
        for version, file in self.files:
            if version == res_version and file.startswith(path):
                yield file


@pytest.fixture
def config(tmp_path: Path) -> Config:
    version_file = tmp_path / "version.json"
    version_file.write_text(
        json.dumps(
            {
                "CN": {"resVersion": CN_VERSION, "clientVersion": "2.7.71"},
                "JP": {"resVersion": "jp-1", "clientVersion": "1"},
            }
        )
    )
    server = {
        "folder": "",
        "updateMsg": "{0} {1}",
        "configUrl": "https://conf.example/",
        "chatMask": "x",
    }
    return Config.model_validate(
        {
            "apiUrl": "https://wiki.example/api.php",
            "torappuUrl": "https://torappu.example",
            "version": str(version_file),
            "serverList": {
                "CN": {**server, "folder": "zh_CN"},
                "JP": {**server, "folder": "ja_JP"},
            },
            "chatMaskList": ["x"],
        }
    )


@pytest.fixture
def gamedata(config: Config, tmp_path: Path) -> GameData:
    yostar = tmp_path / "yostar"
    (yostar / "ja_JP" / "gamedata" / "excel").mkdir(parents=True)
    (yostar / "ja_JP" / "gamedata" / "excel" / "skill_table.json").write_text(
        '{"jp": true}', encoding="utf-8"
    )
    data = GameData(config, yostar_dir=yostar, cache_dir=tmp_path / "cache")
    data.torappu = FakeTorappu(  # type: ignore[assignment]
        {
            (CN_VERSION, "excel/item_table.json"): b'{"items": {"1": {}}}',
            (CN_VERSION, "levels/obt/main/level_main_01-01.json"): b'{"options": 1}',
            (CN_VERSION, "story/[uc]info/x.txt"): "剧情\n".encode(),
        }
    )
    return data


def fake(data: GameData) -> Any:
    return data.torappu


def test_cn_json_comes_from_torappu_and_excel_is_cached_in_memory(
    gamedata: GameData,
) -> None:
    assert gamedata.get("excel/item_table.json") == {"items": {"1": {}}}
    assert gamedata.get("excel/item_table.json") == {"items": {"1": {}}}
    assert fake(gamedata).fetches == [(CN_VERSION, "excel/item_table.json")]


def test_cn_files_are_cached_on_disk_per_version(
    gamedata: GameData, tmp_path: Path
) -> None:
    path = "levels/obt/main/level_main_01-01.json"
    assert gamedata.get(path) == {"options": 1}
    cached = tmp_path / "cache" / CN_VERSION / path
    assert cached.read_bytes() == b'{"options": 1}'
    # 非 excel 不进内存缓存,但第二次读走磁盘缓存,不再请求
    assert gamedata.get(path) == {"options": 1}
    assert fake(gamedata).fetches == [(CN_VERSION, path)]
    assert not list((tmp_path / "cache").rglob("*.part"))


def test_cn_text_and_missing_file(gamedata: GameData) -> None:
    assert gamedata.get_txt("story/[uc]info/x.txt") == "剧情\n"
    with pytest.raises(FileNotFoundError):
        gamedata.get_txt("story/[uc]info/missing.txt")


def test_version_bump_reads_new_version(gamedata: GameData) -> None:
    gamedata.unpacker.version["CN"]["resVersion"] = "new-version"
    assert gamedata.res_version() == "new-version"
    with pytest.raises(FileNotFoundError):
        gamedata.get("excel/item_table.json")
    assert fake(gamedata).fetches == [("new-version", "excel/item_table.json")]


def test_yostar_regions_read_submodule_directory(gamedata: GameData) -> None:
    assert gamedata.get("excel/skill_table.json", "JP") == {"jp": True}
    assert gamedata.list_files("excel", "JP") == ["excel/skill_table.json"]
    assert fake(gamedata).fetches == []


def test_list_files_cn_uses_torappu_walk(gamedata: GameData) -> None:
    assert gamedata.list_files("levels") == ["levels/obt/main/level_main_01-01.json"]
