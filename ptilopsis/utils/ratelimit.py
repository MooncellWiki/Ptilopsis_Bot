"""MediaWiki 写操作限速:登录时发现的配额 + 本地滑动窗口 + 撞限冷却。

``meta=userinfo&uiprop=ratelimits`` 只给适用于当前账号的配额上限(``hits``
是窗口内允许的最大次数,不是已用次数),不给实时余量;服务器窗口的起点也和
本地对不齐。所以这里记下最近的发送时刻,保证任意 ``period`` 长的区间内至多
``limit * safety`` 次。服务器(WRStats)把窗口切成 30 个桶,滑出一半的桶按
比例计数,超过 ``period`` 的请求还会被部分计入;再加上网络延迟,本地记账
和服务器计数会有少许出入,这些由 ``safety`` 留出的余量吸收。本进程之外的
用量(上一次运行、共用账号或 IP 的其它客户端)导致的漏网由撞限错误兜底:
收到 ``ratelimited`` 后按窗口时长冷却再重试。配额为空(如账号有
``noratelimit`` 权限)时所有限速器都是 passthrough,不产生任何等待。
"""

import math
import time
from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import anyio

__all__ = [
    "DEFAULT_COOLDOWN",
    "RateLimit",
    "SlidingWindow",
    "Throttle",
    "parse_ratelimits",
]

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
) -> dict[str, tuple[RateLimit, ...]]:
    """把 ``userinfo.ratelimits`` 转成 ``{action: 服务器实际检查的配额}``。

    接口会把账号沾边的类别全列出来,选取规则同 MediaWiki 的 ``RateLimiter``:
    按账号计数的那条里 ``newbie`` 覆盖其余,否则在 ``user`` 与各用户组中取最
    宽松的;``ip`` / ``subnet`` / ``anon`` 等是独立计数器。服务器一次请求要
    同时过所有计数器,所以这些配额全部保留,只去掉被另一条完全覆盖的(次数
    不多于它、窗口不短于它)。任何一条 ``hits <= 0`` 表示动作被完全禁止而不
    是限速,本地无从等待,跳过。字段缺失或不是数字的类别单独跳过,不影响其它
    条目。
    """
    result: dict[str, tuple[RateLimit, ...]] = {}
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
        if not counters or any(rl.limit <= 0 for rl in counters):
            continue
        distinct = list(dict.fromkeys(counters))
        # 次数不多、窗口不短的那条满足了,被它覆盖的那条自然满足
        kept = [
            rl
            for rl in distinct
            if not any(
                other != rl and other.limit <= rl.limit and other.period >= rl.period
                for other in distinct
            )
        ]
        result[action] = tuple(sorted(kept, key=lambda rl: rl.period))
    return result


class SlidingWindow:
    """一个配额窗口:任意 ``period`` 长的区间内至多放行 ``floor(limit * safety)``
    次(至少 1 次)。额度可以一口气用完,之后等最早的那次滑出窗口。

    本身不等待,由 :class:`Throttle` 在所有窗口都有空位时统一记账。
    """

    def __init__(self, limit: int, period: float, safety: float = 1.0) -> None:
        if limit <= 0:
            # hits=0 是"动作被禁止",不是一个可等待的限速
            raise ValueError("limit must be positive")
        if period <= 0:
            raise ValueError("period must be positive")
        if safety <= 0:
            raise ValueError("safety must be positive")
        self.period = period
        self.max_hits = max(1, math.floor(limit * safety))
        self._expires: deque[float] = deque()
        """已放行请求滑出窗口的时刻,从早到晚。"""

    def delay(self, now: float) -> float:
        """还要等多久才有空位;0 表示现在就能放行。"""
        while self._expires and self._expires[0] <= now:
            self._expires.popleft()
        if len(self._expires) < self.max_hits:
            return 0.0
        return self._expires[0] - now

    def record(self, now: float) -> None:
        self._expires.append(now + self.period)


class Throttle:
    """一个写动作的限速器:同时满足该动作的全部配额窗口;没有窗口时是 passthrough。"""

    def __init__(self, limits: Iterable[RateLimit] = (), safety: float = 1.0) -> None:
        self.windows = tuple(
            SlidingWindow(rl.limit, rl.period, safety=safety) for rl in limits
        )

    async def acquire(self) -> None:
        """占一个名额;有窗口已满时睡到所有窗口都有空位,再一起记账。

        不能逐个窗口 acquire:先占到的窗口会在等别的窗口时提前记账,
        提前把名额放出来。
        """
        while True:
            now = time.monotonic()
            delay = max((w.delay(now) for w in self.windows), default=0.0)
            if delay <= 0:
                for window in self.windows:
                    window.record(now)
                return
            await anyio.sleep(delay)

    async def cooldown(self) -> None:
        """撞限后冷却,等服务器计数器翻页。

        ``ratelimited`` 不说是哪个计数器撞的,按最长的窗口等;没有窗口信息
        就按默认值。
        """
        await anyio.sleep(
            max((w.period for w in self.windows), default=DEFAULT_COOLDOWN)
        )
