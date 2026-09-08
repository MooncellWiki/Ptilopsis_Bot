"""统一的游戏数据访问入口。

* 国服(CN)数据来自 torappu(https://torappu.prts.wiki),按版本文件里记录的
  ``resVersion`` 在线读取,下载过的文件缓存在 ``.cache/torappu/<resVersion>/``;
* 海外服(JP / US / KR)仍然读取 ``thirdparty/ArknightsGameData_YoStar`` 子模块。
"""

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

from ptilopsis.log import logger
from ptilopsis.utils.torappu import TorappuClient
from ptilopsis.utils.unpacker import Unpacker

if TYPE_CHECKING:
    from ptilopsis.config import Config

YOSTAR_DIR = "thirdparty/ArknightsGameData_YoStar"
CACHE_DIR = ".cache/torappu"


class GameData:
    def __init__(
        self,
        config: "Config",
        yostar_dir: str | os.PathLike[str] = YOSTAR_DIR,
        cache_dir: str | os.PathLike[str] = CACHE_DIR,
    ) -> None:
        self.data: dict[tuple[str, str], object] = {}
        """跨 job 的内存缓存,只放 excel 表。"""
        self.config = config
        self.torappu = TorappuClient(config.torappu_url)
        self.unpacker = Unpacker(config, torappu=self.torappu)
        self.yostar_dir = Path(yostar_dir)
        self.cache_dir = Path(cache_dir)
        logger.info(f"CN gamedata source: torappu {config.torappu_url}")

    # ----- 对外接口 -----

    def get(self, path: str, region: str = "CN"):
        """``gamedata/<path>`` 解码后的 JSON。"""
        key = (region, path)
        if key in self.data:
            return self.data[key]
        data = json.loads(self._read_bytes(path, region))
        if "excel" in path:
            self.data[key] = data
        return data

    def get_txt(self, path: str, region: str = "CN") -> str:
        """``gamedata/<path>`` 的原始文本(剧情等非 JSON 文件)。"""
        return self._read_bytes(path, region).decode("utf-8")

    def list_files(self, path: str, region: str = "CN") -> list[str]:
        """递归列出 ``gamedata/<path>`` 下的全部文件,返回相对 gamedata 根的路径。"""
        if self._is_torappu(region):
            return sorted(self.torappu.walk(self.res_version(region), path))
        root = self._yostar_root(region)
        target = root / path
        if target.is_file():
            return [path]
        return sorted(
            str(Path(dirpath, name).relative_to(root))
            for dirpath, _, names in os.walk(target)
            for name in names
            if name != ".DS_Store"
        )

    def res_version(self, region: str = "CN") -> str:
        """当前使用的资源版本(内存中的,``check_update`` 后即为最新)。"""
        return self.unpacker.version[region]["resVersion"]

    # ----- 读取 -----

    def _is_torappu(self, region: str) -> bool:
        return region == "CN"

    def _yostar_root(self, region: str) -> Path:
        return self.yostar_dir / self.config.server_list[region].folder / "gamedata"

    def _read_bytes(self, path: str, region: str) -> bytes:
        if self._is_torappu(region):
            return self._read_torappu(path, region)
        return (self._yostar_root(region) / path).read_bytes()

    def _read_torappu(self, path: str, region: str) -> bytes:
        res_version = self.res_version(region)
        cached = self.cache_dir / res_version / path
        if cached.is_file():
            return cached.read_bytes()
        content = self.torappu.fetch(res_version, path)
        cached.parent.mkdir(parents=True, exist_ok=True)
        # 先写临时文件再改名,中途失败不会留下半截缓存
        tmp = cached.with_name(cached.name + ".part")
        tmp.write_bytes(content)
        os.replace(tmp, cached)
        return content
