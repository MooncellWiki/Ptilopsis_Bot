"""项目统一的 HTTP 客户端与重试辅助。

所有出网请求都走 httpx2 的 :class:`httpx2.AsyncClient`(anyio 后端):

* 开 HTTP/2,几千个小文件可以在一条连接上多路复用;
* connect 超时压短。CDN 域名通常有 8 个 A 记录,anyio 的 Happy Eyeballs 会并发
  试连,个别节点对 CI 出口不通时不会把整个 connect 超时吃满;
* 固定 User-Agent,方便服务端识别。
"""

from typing import Any

import httpx2

from ptilopsis.log import logger

__all__ = ["DEFAULT_CONNECT_TIMEOUT", "USER_AGENT", "log_retry", "make_client"]

USER_AGENT = "Ptilopsis_Bot (+https://github.com/MooncellWiki/Ptilopsis_Bot)"

DEFAULT_CONNECT_TIMEOUT = 10
"""连接超时(秒)。连不上就该尽快换下一个地址,而不是等满 60 秒。"""


def make_client(timeout: float = 60, **kwargs: Any) -> httpx2.AsyncClient:
    """HTTP/2、短 connect 超时、固定 UA 的客户端;``kwargs`` 透传给 AsyncClient。"""
    headers = {"User-Agent": USER_AGENT, **kwargs.pop("headers", {})}
    return httpx2.AsyncClient(
        http2=True,
        timeout=httpx2.Timeout(timeout, connect=DEFAULT_CONNECT_TIMEOUT),
        headers=headers,
        **kwargs,
    )


def log_retry(name: str) -> Any:
    """tenacity 的 ``before_sleep`` 回调:重试前把调用与异常记到日志。"""

    def _before_sleep(retry_state: Any) -> None:
        exc = (
            retry_state.outcome.exception()
            if retry_state.outcome and retry_state.outcome.failed
            else None
        )
        # 跳过 self
        args = retry_state.args[1:] if retry_state.args else ()
        call_args = ", ".join(
            [
                *(repr(a) for a in args),
                *(f"{k}={v!r}" for k, v in retry_state.kwargs.items()),
            ]
        )
        logger.warning(f"Retrying {name}({call_args}) after failure: {exc!r}")

    return _before_sleep
