"""统一的游戏数据访问入口。

* 国服(CN)数据来自 torappu(https://torappu.prts.wiki),按版本文件里记录的
  ``resVersion`` 在线读取,下载过的文件缓存在 ``.cache/torappu/<resVersion>/``;
* 海外服(JP / US / KR)仍然读取 ``thirdparty/ArknightsGameData_YoStar`` 子模块。

读取接口都是 async 的。一个 job 要读很多小文件(剧情简介、关卡)时先
:meth:`GameData.prefetch` 一把,它用 task group 并发下载进缓存,之后的
:meth:`GameData.get` / :meth:`GameData.get_txt` 直接命中磁盘。
"""

import json
import os
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import anyio

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
        torappu: TorappuClient | None = None,
    ) -> None:
        self.data: dict[tuple[str, str], Any] = {}
        """跨 job 的内存缓存,只放 excel 表。"""
        self.config = config
        self.torappu = torappu or TorappuClient(config.torappu_url)
        self.unpacker = Unpacker(config, torappu=self.torappu)
        self.yostar_dir = Path(yostar_dir)
        self.cache_dir = Path(cache_dir)
        self._missing: set[tuple[str, str]] = set()
        """prefetch 时确认不存在的 (resVersion, path),之后读取直接报错不再请求。"""
        logger.info(f"CN gamedata source: torappu {config.torappu_url}")

    async def aclose(self) -> None:
        await self.torappu.aclose()
        await self.unpacker.aclose()

    # ----- 对外接口 -----

    async def get(self, path: str, region: str = "CN") -> Any:
        """``gamedata/<path>`` 解码后的 JSON。"""
        key = (region, path)
        if key in self.data:
            return self.data[key]
        data = json.loads(await self._read_bytes(path, region))
        if "excel" in path:
            self.data[key] = data
        return data

    async def get_txt(self, path: str, region: str = "CN") -> str:
        """``gamedata/<path>`` 的原始文本(剧情等非 JSON 文件)。"""
        return (await self._read_bytes(path, region)).decode("utf-8")

    async def list_files(self, path: str, region: str = "CN") -> list[str]:
        """递归列出 ``gamedata/<path>`` 下的全部文件,返回相对 gamedata 根的路径。"""
        if self._is_torappu(region):
            files = [f async for f in self.torappu.walk(self.res_version(region), path)]
            return sorted(files)
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

    async def prefetch(self, paths: Iterable[str], region: str = "CN") -> None:
        """并发把 ``paths`` 下载进磁盘缓存;不存在的文件记下来,不算失败。

        海外服数据本来就在本地,直接返回。
        """
        if not self._is_torappu(region):
            return
        res_version = self.res_version(region)
        pending = [
            path
            for path in dict.fromkeys(paths)
            if (res_version, path) not in self._missing
            and not self._cache_path(res_version, path).is_file()
        ]
        if not pending:
            return
        logger.info(f"Prefetching {len(pending)} CN gamedata files from torappu")

        async def fetch_one(path: str) -> None:
            try:
                await self._download(res_version, path)
            except FileNotFoundError:
                self._missing.add((res_version, path))

        async with anyio.create_task_group() as tg:
            for path in pending:
                tg.start_soon(fetch_one, path)

    def res_version(self, region: str = "CN") -> str:
        """当前使用的资源版本(内存中的,``check_update`` 后即为最新)。"""
        return self.unpacker.version[region]["resVersion"]

    # ----- 读取 -----

    def _is_torappu(self, region: str) -> bool:
        return region == "CN"

    def _yostar_root(self, region: str) -> Path:
        return self.yostar_dir / self.config.server_list[region].folder / "gamedata"

    def _cache_path(self, res_version: str, path: str) -> Path:
        return self.cache_dir / res_version / path

    async def _read_bytes(self, path: str, region: str) -> bytes:
        if self._is_torappu(region):
            return await self._read_torappu(path, region)
        return await anyio.Path(self._yostar_root(region) / path).read_bytes()

    async def _read_torappu(self, path: str, region: str) -> bytes:
        res_version = self.res_version(region)
        if (res_version, path) in self._missing:
            raise FileNotFoundError(f"torappu has no {path!r} for {res_version}")
        cached = anyio.Path(self._cache_path(res_version, path))
        if await cached.is_file():
            return await cached.read_bytes()
        return await self._download(res_version, path)

    async def _download(self, res_version: str, path: str) -> bytes:
        content = await self.torappu.fetch(res_version, path)
        cached = anyio.Path(self._cache_path(res_version, path))
        await cached.parent.mkdir(parents=True, exist_ok=True)
        # 先写临时文件再改名,中途失败不会留下半截缓存;临时文件名带随机段,
        # 并发下载同一个文件时也不会互相覆盖
        tmp = cached.with_name(f"{cached.name}.{uuid.uuid4().hex}.part")
        await tmp.write_bytes(content)
        await tmp.replace(cached)
        return content
