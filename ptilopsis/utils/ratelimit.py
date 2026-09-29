"""MediaWiki 写操作限速:登录时发现的配额 + 本地滑动窗口 + 撞限冷却。

``meta=userinfo&uiprop=ratelimits`` 只给适用于当前账号的配额上限(``hits``
是窗口内允许的最大次数,不是已用次数),不给实时余量;服务器窗口的起点也和
本地对不齐。所以这里记下最近的发送时刻,保证任意 ``period`` 长的区间内至多
``limit * safety`` 次,不管服务器怎么划窗口都不会超额。本进程之外的用量
(上一次运行、共用账号的其它客户端)导致的漏网由撞限错误兜底:收到
``ratelimited`` 后按窗口时长冷却再重试。配额为空(如账号有 ``noratelimit``
权限)时所有限速器都是 passthrough,不产生任何等待。
"""

import math
import time
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import anyio

__all__ = ["DEFAULT_COOLDOWN", "RateLimit", "SlidingWindow", "parse_ratelimits"]

DEFAULT_COOLDOWN = 60.0
"""查不到配额窗口时,撞限后的默认冷却秒数。"""

SHARED_CATEGORIES = frozenset(
    {"anon", "ip", "subnet", "ip-all", "subnet-all", "user-global"}
)
"""各自独立计数的类别;其余(``user``、``newbie`` 与各用户组)竞争同一个按账号的计数器。"""


@dataclass(frozen=True)
class RateLimit:
    """一个动作在一个窗口内允许的次数。"""

    limit: int
    period: float

    @property
    def per_second(self) -> float:
        return self.limit / self.period


def parse_ratelimits(
    ratelimits: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, RateLimit]:
    """把 ``userinfo.ratelimits`` 转成 ``{action: RateLimit}``,即服务器实际执行的那条。

    接口会把账号沾边的类别全列出来,选取规则同 MediaWiki 的 ``RateLimiter``:
    按账号计数的那条里 ``newbie`` 覆盖其余,否则在 ``user`` 与各用户组中取最
    宽松的;``ip`` / ``subnet`` / ``anon`` 等是独立计数器,每条都要满足,再和
    按账号的那条一起取最严的。生效的那条 ``hits <= 0`` 表示动作被完全禁止
    而不是限速,本地无从等待,跳过。字段缺失或不是数字的类别单独跳过,不影响
    其它条目。
    """
    result: dict[str, RateLimit] = {}
    for action, categories in ratelimits.items():
        if not isinstance(categories, Mapping):
            continue
        account: dict[str, RateLimit] = {}
        counters: list[RateLimit] = []
        for name, cat in categories.items():
            try:
                rl = RateLimit(int(cat["hits"]), float(cat["seconds"]))
            except (KeyError, TypeError, ValueError):
                continue
            if rl.period <= 0:
                continue
            if name in SHARED_CATEGORIES:
                counters.append(rl)
            else:
                account[name] = rl
        per_account = account.get("newbie") or max(
            account.values(), key=lambda rl: rl.per_second, default=None
        )
        if per_account is not None:
            counters.append(per_account)
        if not counters:
            continue
        effective = min(counters, key=lambda rl: rl.per_second)
        if effective.limit > 0:
            result[action] = effective
    return result


class SlidingWindow:
    """滑动窗口限速器;``limit is None`` 表示无限制,所有等待立即返回。

    任意 ``period`` 长的区间内至多放行 ``floor(limit * safety)`` 次(至少 1 次):
    额度可以一口气用完,之后等最早的那次滑出窗口。
    """

    def __init__(self, limit: int | None, period: float, safety: float = 1.0) -> None:
        if limit is not None and limit <= 0:
            # hits=0 是"动作被禁止",不是一个可等待的限速
            raise ValueError("limit must be positive, or None for unlimited")
        if limit is not None and period <= 0:
            raise ValueError("period must be positive when the limiter is limited")
        if safety <= 0:
            raise ValueError("safety must be positive")
        self.period = period
        self.max_hits = (
            max(1, math.floor(limit * safety)) if limit is not None else None
        )
        self._expires: deque[float] = deque()
        """已放行请求滑出窗口的时刻,从早到晚。"""

    async def acquire(self) -> None:
        """占一个名额;窗口已满时睡到最早的那次滑出去。"""
        if self.max_hits is None:
            return
        while True:
            now = time.monotonic()
            while self._expires and self._expires[0] <= now:
                self._expires.popleft()
            if len(self._expires) < self.max_hits:
                self._expires.append(now + self.period)
                return
            await anyio.sleep(self._expires[0] - now)

    async def cooldown(self) -> None:
        """撞限后冷却一个窗口,等服务器计数器翻页;没有窗口信息就按默认值。"""
        await anyio.sleep(self.period if self.period > 0 else DEFAULT_COOLDOWN)
