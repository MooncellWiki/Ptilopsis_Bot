from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING

from ptilopsis.log import logger

if TYPE_CHECKING:
    from ptilopsis.utils.data import GameData
    from ptilopsis.utils.wiki import Wiki


@dataclass(frozen=True)
class JobContext:
    """所有 job 入口共享的运行上下文：Wiki 客户端 + 游戏数据源。"""

    wiki: "Wiki"
    gamedata: "GameData"

    def getgd(self, path: str, region: str = "CN") -> dict:
        """
        :param path:
        :param region: 服务器: CN,US,JP,KR,TW
        :return: dict
        """
        return self.gamedata.get(path, region)

    def getgd_txt(self, path: str, region: str = "CN") -> str:
        """
        :param path:
        :param region: 服务器: CN,US,JP,KR,TW
        :return: string
        """
        return self.gamedata.get_txt(path, region)


def job[**P, R](func: Callable[P, R]) -> Callable[P, R | None]:
    """把函数标记为 job 入口：统一捕获异常并记录，返回值原样透传。

    用法::

        @job
        def run(ctx: JobContext) -> None:
            table = ctx.getgd("excel/xxx_table.json")
            ctx.wiki.edit(...)
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception(f"job {func.__module__}.{func.__name__} failed")
            return None

    return wrapper
