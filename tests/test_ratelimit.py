"""限速器:配额解析与令牌桶行为,全部离线。"""

import time

import pytest

from ptilopsis.utils.ratelimit import RateLimit, TokenBucket, parse_ratelimits

pytestmark = pytest.mark.anyio


def test_parse_picks_most_restrictive_category() -> None:
    # prts.wiki 实测的响应结构:同一动作可同时适用多个类别,保留最紧的一条
    ratelimits = {
        "edit": {
            "user": {"hits": 90, "seconds": 60},
            "newbie": {"hits": 8, "seconds": 60},
        },
        "purge": {"ip": {"hits": 30, "seconds": 60}},
    }
    assert parse_ratelimits(ratelimits) == {
        "edit": RateLimit(8, 60),
        "purge": RateLimit(30, 60),
    }


def test_parse_skips_empty_and_fully_blocked() -> None:
    # hits=0 是"动作被禁止"而不是限速;空对象是 noratelimit 账号
    assert parse_ratelimits({}) == {}
    assert parse_ratelimits({"blocked": {"user": {"hits": 0, "seconds": 60}}}) == {}


def test_parse_tolerates_malformed_entries() -> None:
    # 单个类别的字段缺失 / 非数字只跳过该条,不影响其余动作
    ratelimits = {
        "edit": {"user": {"hits": "abc", "seconds": 60}, "ip": {"hits": 8}},
        "purge": {"ip": {"hits": 30, "seconds": 60}},
    }
    assert parse_ratelimits(ratelimits) == {"purge": RateLimit(30, 60)}


def test_constructor_validates_arguments() -> None:
    with pytest.raises(ValueError, match="limit"):
        TokenBucket(0, 60)
    with pytest.raises(ValueError, match="period"):
        TokenBucket(10, 0)
    with pytest.raises(ValueError, match="safety"):
        TokenBucket(10, 60, safety=0)
    TokenBucket(None, 0.0)  # 无限制的桶不要求窗口


async def test_unlimited_bucket_never_waits() -> None:
    bucket = TokenBucket(None, 0.0)
    start = time.monotonic()
    for _ in range(100):
        await bucket.acquire()
    assert time.monotonic() - start < 0.5


async def test_bucket_paces_beyond_limit() -> None:
    # 满桶 2 个令牌,补充速率 10/s:前两次立即,第三次要等约 0.1s
    bucket = TokenBucket(2, 0.2, safety=1.0)
    await bucket.acquire()
    await bucket.acquire()
    start = time.monotonic()
    await bucket.acquire()
    assert time.monotonic() - start >= 0.09


async def test_bucket_safety_slows_refill() -> None:
    # safety 0.5 -> 补充速率 5/s,第三个令牌要等约 0.2s
    bucket = TokenBucket(2, 0.2, safety=0.5)
    await bucket.acquire()
    await bucket.acquire()
    start = time.monotonic()
    await bucket.acquire()
    assert time.monotonic() - start >= 0.18


async def test_cooldown_sleeps_window() -> None:
    bucket = TokenBucket(2, 0.05)
    start = time.monotonic()
    await bucket.cooldown()
    assert time.monotonic() - start >= 0.04
