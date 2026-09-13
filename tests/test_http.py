"""HTTP 辅助:重试日志不能带出调用参数里的敏感信息。"""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from tenacity import retry, stop_after_attempt, wait_none

from ptilopsis.log import logger
from ptilopsis.utils.http import log_retry


@pytest.fixture
def messages() -> Iterator[list[str]]:
    captured: list[str] = []
    sink = logger.add(captured.append, format="{message}")
    yield captured
    logger.remove(sink)


def flaky(before_sleep: Any) -> Callable[..., str]:
    """第一次调用超时、第二次成功的"方法"(第一个参数当作 self)。"""
    calls = 0

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_none(),
        before_sleep=before_sleep,
        reraise=True,
    )
    def post(self: object, data: dict[str, str]) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("timed out")
        return "ok"

    return post


def test_log_retry_omits_arguments_by_default(messages: list[str]) -> None:
    post = flaky(log_retry("wiki.post"))
    assert post(object(), {"lgpassword": "hunter2", "lgtoken": "LOGIN"}) == "ok"
    assert len(messages) == 1
    assert "wiki.post" in messages[0] and "TimeoutError" in messages[0]
    assert "hunter2" not in messages[0] and "LOGIN" not in messages[0]


def test_log_retry_with_args_skips_self(messages: list[str]) -> None:
    fetch = flaky(log_retry("fetch", with_args=True))
    assert fetch("SELF", {"path": "excel/item_table.json"}) == "ok"
    assert "excel/item_table.json" in messages[0]
    assert "SELF" not in messages[0]
