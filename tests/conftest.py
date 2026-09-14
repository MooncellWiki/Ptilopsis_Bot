import pytest


@pytest.fixture
def anyio_backend() -> str:
    # 只装了 asyncio 后端;anyio 的 pytest 插件默认还会参数化 trio
    return "asyncio"
