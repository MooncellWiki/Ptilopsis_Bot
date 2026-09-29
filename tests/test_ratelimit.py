"""限速器:配额解析与滑动窗口行为,全部离线。"""

import math
import time
from types import SimpleNamespace

import anyio
import pytest

from ptilopsis.utils import ratelimit
from ptilopsis.utils.ratelimit import (
    DEFAULT_COOLDOWN,
    RateLimit,
    SlidingWindow,
    parse_ratelimits,
)

pytestmark = pytest.mark.anyio


def hits(limit: int, seconds: int = 60) -> dict[str, int]:
    return {"hits": limit, "seconds": seconds}


def test_parse_takes_most_permissive_group() -> None:
    # user 与各用户组竞争同一个按账号的计数器,服务器取最宽松的一条
    ratelimits = {
        "edit": {"user": hits(90), "bot": hits(600), "autoconfirmed": hits(30)},
        "upload": {"user": hits(90), "autoconfirmed": hits(30)},
    }
    assert parse_ratelimits(ratelimits) == {
        "edit": RateLimit(600, 60),
        "upload": RateLimit(90, 60),
    }


def test_parse_newbie_overrides_account_limits() -> None:
    # newbie 覆盖 user 与各用户组;ip / subnet 是独立计数器,和它一起取最严
    ratelimits = {
        "edit": {"user": hits(90), "newbie": hits(8), "bot": hits(600)},
        "purge": {"user": hits(90), "newbie": hits(50), "ip": hits(30)},
    }
    assert parse_ratelimits(ratelimits) == {
        "edit": RateLimit(8, 60),
        "purge": RateLimit(30, 60),
    }


def test_parse_anonymous_shared_counters() -> None:
    # prts.wiki 匿名请求实测的响应结构:只有独立计数的 ip 类别
    ratelimits = {"edit": {"ip": hits(8)}, "renderfile": {"ip": hits(700, 30)}}
    assert parse_ratelimits(ratelimits) == {
        "edit": RateLimit(8, 60),
        "renderfile": RateLimit(700, 30),
    }


def test_parse_skips_empty_and_fully_blocked() -> None:
    # 生效的那条 hits=0 是"动作被禁止"而不是限速;空对象是 noratelimit 账号
    assert parse_ratelimits({}) == {}
    assert parse_ratelimits({"blocked": {"user": hits(0)}}) == {}
    assert parse_ratelimits({"edit": {"user": hits(90), "newbie": hits(0)}}) == {}
    # 被更宽松的 user 盖过的 0 不算禁止
    assert parse_ratelimits({"edit": {"user": hits(90), "blocked": hits(0)}}) == {
        "edit": RateLimit(90, 60)
    }


def test_parse_tolerates_malformed_entries() -> None:
    # 单个类别的字段缺失 / 非数字只跳过该条,不影响其余动作
    ratelimits = {
        "edit": {"user": {"hits": "abc", "seconds": 60}, "ip": {"hits": 8}},
        "move": {"user": hits(10, 0)},
        "noratelimit": "",
        "purge": {"ip": hits(30)},
    }
    assert parse_ratelimits(ratelimits) == {"purge": RateLimit(30, 60)}


def test_constructor_validates_arguments() -> None:
    with pytest.raises(ValueError, match="limit"):
        SlidingWindow(0, 60)
    with pytest.raises(ValueError, match="period"):
        SlidingWindow(10, 0)
    with pytest.raises(ValueError, match="safety"):
        SlidingWindow(10, 60, safety=0)
    SlidingWindow(None, 0.0)  # 无限制的限速器不要求窗口


def test_safety_scales_hits_per_window() -> None:
    assert SlidingWindow(90, 60, safety=0.8).max_hits == 72
    assert SlidingWindow(8, 60, safety=0.8).max_hits == 6
    # 再保守也至少放行一次,否则永远发不出去
    assert SlidingWindow(1, 60, safety=0.5).max_hits == 1


async def test_unlimited_never_waits() -> None:
    limiter = SlidingWindow(None, 0.0)
    start = time.monotonic()
    for _ in range(100):
        await limiter.acquire()
    assert time.monotonic() - start < 0.5


async def test_window_paces_beyond_limit() -> None:
    # 窗口 0.2s 内 2 次:前两次立即,第三次要等第一次滑出窗口
    limiter = SlidingWindow(2, 0.2)
    await limiter.acquire()
    await limiter.acquire()
    start = time.monotonic()
    await limiter.acquire()
    assert time.monotonic() - start >= 0.18


@pytest.mark.parametrize(
    ("limit", "period", "safety", "latency"),
    [(90, 60, 0.8, 0.25), (8, 60, 0.8, 0.5), (8, 60, 1.0, 0.0), (3, 10, 0.5, 2.0)],
)
async def test_never_exceeds_quota_in_any_window(
    monkeypatch: pytest.MonkeyPatch,
    limit: int,
    period: float,
    safety: float,
    latency: float,
) -> None:
    # 假时钟下持续写 10 分钟:任意一个 period 长的区间内都不超过 limit * safety。
    # 耗时取二进制下精确的值,免得浮点误差让睡醒时刻差一点点、反复睡极短的时间
    now = 0.0

    async def advance(seconds: float) -> None:
        nonlocal now
        now += seconds

    monkeypatch.setattr(ratelimit, "time", SimpleNamespace(monotonic=lambda: now))
    monkeypatch.setattr(anyio, "sleep", advance)
    limiter = SlidingWindow(limit, period, safety)
    sent: list[float] = []
    while now < 600:
        await limiter.acquire()
        sent.append(now)
        now += latency
    allowed = math.floor(limit * safety)
    for i, start in enumerate(sent):
        in_window = sum(1 for t in sent[i:] if t < start + period)
        assert in_window <= allowed
    # 也不能过度保守:10 分钟里用满每个窗口的额度
    assert len(sent) >= allowed * (600 // period)


async def test_cooldown_sleeps_window(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(anyio, "sleep", record)
    await SlidingWindow(2, 30).cooldown()
    # 查不到配额的动作没有窗口信息,按默认值冷却
    await SlidingWindow(None, 0.0).cooldown()
    assert slept == [30, DEFAULT_COOLDOWN]
