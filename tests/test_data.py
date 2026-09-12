"""GameData:国服走 torappu(带缓存与并发预取),海外服走子模块目录。"""

import json
from pathlib import Path
from typing import Any

import anyio
import pytest

from ptilopsis.config import Config
from ptilopsis.utils.data import GameData

pytestmark = pytest.mark.anyio

CN_VERSION = "26-09-03-04-06-00_ed95a2"


class FakeTorappu:
    def __init__(self, files: dict[tuple[str, str], bytes]) -> None:
        self.files = files
        self.fetches: list[tuple[str, str]] = []
        self.in_flight = 0
        self.max_in_flight = 0

    async def fetch(self, res_version: str, path: str) -> bytes:
        self.fetches.append((res_version, path))
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        await anyio.sleep(0.01)
        self.in_flight -= 1
        try:
            return self.files[(res_version, path)]
        except KeyError:
            raise FileNotFoundError(path) from None

    async def walk(self, res_version: str, path: str):
        for version, file in self.files:
            if version == res_version and file.startswith(path):
                yield file

    async def aclose(self) -> None:
        pass


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
    torappu = FakeTorappu(
        {
            (CN_VERSION, "excel/item_table.json"): b'{"items": {"1": {}}}',
            (CN_VERSION, "levels/obt/main/level_main_01-01.json"): b'{"options": 1}',
            (CN_VERSION, "story/[uc]info/x.txt"): "剧情\n".encode(),
            (CN_VERSION, "story/[uc]info/y.txt"): b"y",
        }
    )
    return GameData(
        config,
        yostar_dir=yostar,
        cache_dir=tmp_path / "cache",
        torappu=torappu,  # type: ignore[arg-type]
    )


def fake(data: GameData) -> Any:
    return data.torappu


async def test_cn_json_comes_from_torappu_and_excel_is_cached_in_memory(
    gamedata: GameData,
) -> None:
    assert await gamedata.get("excel/item_table.json") == {"items": {"1": {}}}
    assert await gamedata.get("excel/item_table.json") == {"items": {"1": {}}}
    assert fake(gamedata).fetches == [(CN_VERSION, "excel/item_table.json")]


async def test_cn_files_are_cached_on_disk_per_version(
    gamedata: GameData, tmp_path: Path
) -> None:
    path = "levels/obt/main/level_main_01-01.json"
    assert await gamedata.get(path) == {"options": 1}
    cached = tmp_path / "cache" / CN_VERSION / path
    assert cached.read_bytes() == b'{"options": 1}'
    # 非 excel 不进内存缓存,但第二次读走磁盘缓存,不再请求
    assert await gamedata.get(path) == {"options": 1}
    assert fake(gamedata).fetches == [(CN_VERSION, path)]
    assert not list((tmp_path / "cache").rglob("*.part"))


async def test_cn_text_and_missing_file(gamedata: GameData) -> None:
    assert await gamedata.get_txt("story/[uc]info/x.txt") == "剧情\n"
    with pytest.raises(FileNotFoundError):
        await gamedata.get_txt("story/[uc]info/missing.txt")


async def test_version_bump_reads_new_version(gamedata: GameData) -> None:
    gamedata.unpacker.version["CN"]["resVersion"] = "new-version"
    assert gamedata.res_version() == "new-version"
    with pytest.raises(FileNotFoundError):
        await gamedata.get("excel/item_table.json")
    assert fake(gamedata).fetches == [("new-version", "excel/item_table.json")]


async def test_yostar_regions_read_submodule_directory(gamedata: GameData) -> None:
    assert await gamedata.get("excel/skill_table.json", "JP") == {"jp": True}
    assert await gamedata.list_files("excel", "JP") == ["excel/skill_table.json"]
    assert fake(gamedata).fetches == []


async def test_list_files_cn_uses_torappu_walk(gamedata: GameData) -> None:
    assert await gamedata.list_files("levels") == [
        "levels/obt/main/level_main_01-01.json"
    ]


async def test_prefetch_downloads_concurrently_and_remembers_missing(
    gamedata: GameData, tmp_path: Path
) -> None:
    paths = ["story/[uc]info/x.txt", "story/[uc]info/y.txt", "story/[uc]info/nope.txt"]
    await gamedata.prefetch(paths)
    torappu = fake(gamedata)
    assert sorted(p for _, p in torappu.fetches) == sorted(paths)
    assert torappu.max_in_flight > 1
    assert (
        tmp_path / "cache" / CN_VERSION / "story/[uc]info/y.txt"
    ).read_bytes() == b"y"

    # 之后读取全部走缓存/记忆,不再产生请求;缺失的文件立刻报错
    torappu.fetches.clear()
    assert await gamedata.get_txt("story/[uc]info/x.txt") == "剧情\n"
    with pytest.raises(FileNotFoundError):
        await gamedata.get_txt("story/[uc]info/nope.txt")
    assert torappu.fetches == []

    # 再次 prefetch 同样的路径是空操作
    await gamedata.prefetch(paths)
    assert torappu.fetches == []


async def test_prefetch_is_noop_for_yostar(gamedata: GameData) -> None:
    await gamedata.prefetch(["excel/skill_table.json"], "JP")
    assert fake(gamedata).fetches == []
