"""MediaWiki 写操作限速:登录时发现的配额 + 本地令牌桶 + 撞限冷却。

``meta=userinfo&uiprop=ratelimits`` 只给适用于当前账号的配额上限(``hits``
是窗口内允许的最大次数,不是已用次数),不给实时余量;服务器内部是固定窗口
计数器。所以这里用令牌桶按配额的 ``safety`` 比例补充令牌来模拟用量,本地
窗口与服务器对不齐导致的漏网由撞限错误兜底:收到 ``ratelimited`` 后按窗口
时长冷却再重试。配额为空(如账号有 ``noratelimit`` 权限)时所有桶都是
passthrough,不产生任何等待。
"""

import math
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import anyio

__all__ = ["DEFAULT_COOLDOWN", "RateLimit", "TokenBucket", "parse_ratelimits"]

DEFAULT_COOLDOWN = 60.0
"""查不到配额窗口时,撞限后的默认冷却秒数。"""


@dataclass(frozen=True)
class RateLimit:
    """一个动作在一个窗口内允许的次数。"""

    limit: int
    period: float


def parse_ratelimits(
    ratelimits: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, RateLimit]:
    """把 ``userinfo.ratelimits`` 转成 ``{action: RateLimit}``。

    同一动作可能同时适用多个类别(user / newbie / ip ...),服务器按其中最紧
    的一条计,这里同样只保留补充速率最低的一条。``hits <= 0`` 表示动作被完全
    禁止而不是限速,本地无从等待,跳过。
    """
    result: dict[str, RateLimit] = {}
    for action, categories in ratelimits.items():
        candidates = [
            RateLimit(int(cat["hits"]), float(cat["seconds"]))
            for cat in categories.values()
            if int(cat.get("hits", 0)) > 0 and float(cat.get("seconds", 0)) > 0
        ]
        if candidates:
            result[action] = min(candidates, key=lambda rl: rl.limit / rl.period)
    return result


class TokenBucket:
    """令牌桶;``limit is None`` 表示无限制,所有等待立即返回。

    桶初始是满的(登录后立刻允许配额允许的突发,和服务器的固定窗口一致),
    令牌按 ``limit * safety / period`` 的速率补充。
    """

    def __init__(self, limit: int | None, period: float, safety: float = 1.0) -> None:
        if limit and safety <= 0:
            raise ValueError("safety must be positive")
        self.period = period
        self._capacity = float(limit) if limit else math.inf
        self._rate = limit * safety / period if limit else math.inf
        self._tokens = self._capacity
        self._updated = time.monotonic()

    async def acquire(self) -> None:
        """取一个令牌;不足时睡到补充出来。"""
        if math.isinf(self._rate):
            return
        while True:
            now = time.monotonic()
            self._tokens = min(
                self._capacity, self._tokens + (now - self._updated) * self._rate
            )
            self._updated = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return
            await anyio.sleep((1.0 - self._tokens) / self._rate)

    async def cooldown(self) -> None:
        """撞限后冷却一个窗口,等服务器计数器翻页;没有窗口信息就按默认值。"""
        await anyio.sleep(self.period if self.period > 0 else DEFAULT_COOLDOWN)
